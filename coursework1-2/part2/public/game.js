var socket = null;

var app = new Vue({
    el: '#app',
    data: {
        displayUsername: "",
        connected: false,
        loggedIn: false,
        loading: true,
        audience: false,
        admin: false,
        players: [],
        score: 0,
        gameState: 1,
        currentRound: 1,
        promptAnswer: '',
        showPromptBox: false,
        userPrompt: '',
        isRegistering: false,
        gameInfo: {
            2: { success: false },
            3: { prompts: [] },
            4: { allowed: true, vote: [], prompt: '' },
            5: { voteResults: [], prompt: '' },
            6: []
        },
        promptAnswers: {
            name: ['a', 'b', 'c']
        }
    },
    computed: {
        sortedFinalScores() {
            return [...this.gameInfo[6]].sort((a, b) => b[1] - a[1]);
        },
        finalPodium() {
            return this.sortedFinalScores.slice(0, 3);
        }
    },
    mounted: function () {
        if (!socket) {
            connect();
        }
    },
    methods: {
        login() {
            if (!this.username || !this.password) {
                alert('Username or password is empty');
                return;
            }
            this.isRegistering = false;
            const loginData = { user: this.username, pwd: this.password };
            socket.emit('login', loginData);
            this.displayUsername = this.username;
        },
        register() {
            if (!this.username || !this.password) {
                alert('Username or password is empty');
                return;
            }
            this.isRegistering = true;
            const registerData = { user: this.username, pwd: this.password };
            socket.emit('register', registerData);
             this.displayUsername = this.username;
        },
        togglePromptBox() {
            this.showPromptBox = !this.showPromptBox;
            if (this.showPromptBox) {
                this.gameInfo[2].success = false;
            }
        },

        cancelPrompt() {
            this.showPromptBox = false;
            this.userPrompt = '';
            this.gameInfo[2].success = false;
        },

        sendPrompt() {
            if (!this.userPrompt) {
                alert('Prompt is empty');
                return;
            }
            if (this.userPrompt.length > 100 || this.userPrompt.length < 20) {
                alert('Prompt must be more than 20 characters and less than 100');
                return;
            }
            const data = { prompt: this.userPrompt };
            socket.emit('userPrompt', data);
        },
        startGame() {
            socket.emit('admin', 'start');
        },
        adminNext() {
            socket.emit('admin', 'next');
        },
        newGame() {
            socket.emit('admin', 'reset');
        },
        sendAnswer(promptSent) {
            const userAnswer = this.ans;
            if (!userAnswer) {
                alert('Prompt is empty');
                return;
            }
            const data = { answer: userAnswer, prompt: promptSent };
            socket.emit('userAnswer', data);
            const promptArray = this.gameInfo[3].prompts;
            promptArray.splice(0, 1);
            this.ans = "";
        },
        voteForAnswer(voteResult) {
            const data = {
                answer: voteResult,
                prompt: this.gameInfo[4].prompt
            };
            socket.emit('vote', data);

            this.gameInfo[4].allowed = false;
            this.gameInfo[4].vote = [];
            this.gameInfo[4].prompt = '';
        }
    }
});

var display = new Vue({
    el: '#display',
    data: {
        gameState: 1,
        joinUrl: window.location.origin,
        players: [],
        audience: [],
        promptCount: 0,
        promptAuthors: [],
        adminName: '',
        answeredPlayers: [],
        waitingPlayers: [],
        votedPlayers: [],
        waitingVoters: [],
        prompt: "",
        ans1: "",
        ans2: "",
        res: [],
        scores: []
    },
    computed: {
        sortedScores() {
            return [...this.scores].sort((a, b) => b[1] - a[1]);
        },
        podium() {
            return this.sortedScores.slice(0, 3);
        }
    },
    mounted: function () {
        if (!socket) {
            connect();
        }
    }
});

function connect() {
    if (socket) return;
    socket = io();

    socket.on('connect', function () {
        app.connected = true;
    });

    socket.on('adminAssigned', function (name) {
        display.adminName = name || '';
    });

    socket.on('connect_error', function (message) {
        alert('Unable to connect: ' + message);
    });

    socket.on('loggedIn', function (res) {
        if (res) {
            alert('Login successful!');
            app.loggedIn = true;
        } else {
            app.loggedIn = false;
        }
    });

    socket.on('loginResponse', function (message) {
        const wasRegistering = app.isRegistering;
        app.isRegistering = false;

        if (wasRegistering) {
            alert('Registration successful! You are now logged in.');
        }

        if (message === 'admin') {
            app.admin = true;
        } else if (message === 'audience') {
            app.audience = true;
        }

        if (message === 'admin') {
            alert('You are the admin player. You can start and advance the game from your device.');
        }
    });


    socket.on('gameState', function (state) {
        app.gameState = state;
        display.gameState = state;

        if (state === 2) {
            app.gameInfo[2].success = false;
        } else if (state === 3) {
            app.gameInfo[3].prompts = [];
        }
    });

    socket.on('updatedPlayers', function (data) {
        const playersList = data.players || [];
        const audienceList = data.audience || [];

        app.players = playersList;
        display.players = playersList;
        display.audience = audienceList;
    });

    socket.on('promptResponse', function (success) {
        if (success) {
            app.gameInfo[2].success = true;
            app.userPrompt = '';
            app.showPromptBox = false;
        }
    });

    socket.on('promptToAnswer', function (prompt) {
        app.gameInfo[3].prompts.push(prompt);
    });

    socket.on('voteData', function(answers) {
        app.gameInfo[4].allowed = answers.allowedToVote;

        if (answers.allowedToVote) {
            const opts = answers.vote || [];

            while (opts.length < 2) {
                opts.push('');
            }

            app.gameInfo[4].vote = opts;
            app.gameInfo[4].prompt = answers.prompt;
        } else {
            app.gameInfo[4].vote = [];
            app.gameInfo[4].prompt = '';
        }
    });

    socket.on('voteResults', function (results) {
        app.gameInfo[5].prompt = results.prompt;
        app.gameInfo[5].voteResults = results.voteResults;
    });

    socket.on('errorMessage', function (message) {
        alert(message);
    });

    socket.on('round', function (message) {
        app.currentRound = message;
    });

    socket.on('scores', function (message) {
        app.gameInfo[6] = message;
    });

    socket.on('promptStats', function (data) {
        display.promptCount = data.count;
        display.promptAuthors = data.authors || [];
    });

    socket.on('answerStats', function (data) {
        display.answeredPlayers = data.answered;
        display.waitingPlayers = data.waiting;
    });

    socket.on('voteStats', function (data) {
        display.votedPlayers = data.voted;
        display.waitingVoters = data.waiting;
    });

    socket.on('displayAns', function (data) {
        display.prompt = data.prompt;
        display.ans1 = data.ans1;
        display.ans2 = data.ans2;
    });

    socket.on('displayRes', function (data) {
        display.prompt = data.prompt;
        display.res = data.voteResults;
    });

    socket.on('displayScores', function (data) {
        display.scores = data;
    });

    socket.on('disconnect', function () {
        alert('Disconnected');
        app.connected = false;
    });
}
