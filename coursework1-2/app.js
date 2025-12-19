'use strict';

const express = require('express');
const app = express();
const server = require('http').Server(app);
const io = require('socket.io')(server);
const fetch = (...args) =>
  import('node-fetch').then(({ default: fetch }) => fetch(...args));

const BACKEND_ENDPOINT = process.env.BACKEND || 'http://localhost:8181';
const AZURE_API_KEY = process.env.AZURE_API_KEY || null;

app.set('view engine', 'ejs');
app.use('/static', express.static('public'));

app.get('/', (req, res) => res.render('client'));
app.get('/display', (req, res) => res.render('display'));

const GameStates = {
  JOINING: 1,
  PROMPTS: 2,
  ANSWERS: 3,
  VOTING: 4,
  RESULTS: 5,
  SCORES: 6,
  GAME_OVER: 7
};

let gameState = GameStates.JOINING;
let admin = '';
let round = 0;

let players = new Map();
let playerToSocket = new Map();
let socketToPlayer = new Map();
let audienceToSocket = new Map();
let socketToAudience = new Map();

let prompts = [];
let promptAllocation = new Map();
let voteResults = new Map();
let voteVoters = new Map();
let usedPrompts = [];
let promptsForRound = [];
let savedPromptTexts = new Set();

let promptsSubmitted = new Set();
let answersSubmitted = new Set();
let votesReceived = new Set();

let readyToVote = false;
let currentVote = '';

async function callAzureAPI(endpoint, method, body = null) {
  const url = `${BACKEND_ENDPOINT}${endpoint}`;
  const upperMethod = method.toUpperCase();

  const options = {
    method: upperMethod,
    headers: {
      'Content-Type': 'application/json'
    }
  };

  if (AZURE_API_KEY) {
    options.headers['x-functions-key'] = AZURE_API_KEY;
  }

  if (body && upperMethod !== 'GET') {
    options.body = JSON.stringify(body);
  }

  const response = await fetch(url, options);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

function registerUser(username, password, socket) {
  callAzureAPI('/player/register', 'POST', { username, password })
    .then(json => {
      if (json.result) {
        const gameStarted = gameState >= GameStates.PROMPTS;

        if (gameStarted || players.size >= 8) {
          socket.emit('loginResponse', 'audience');
          addNewAudience(username, socket);
        } else {
          addNewUser(username, password, socket);
        }
      } else {
        socket.emit('errorMessage', json.msg);
      }
    })
    .catch(error => {
      console.error('Registration error:', error);
      socket.emit('errorMessage', 'Unable to connect to server. Please try again.');
    });
}

function loginUser(username, password, socket) {
  console.log(`${username} attempting login`);

  callAzureAPI('/player/login', 'POST', { username, password })
    .then(json => {
      if (json.result) {
        console.log(`${username} logged in successfully`);
        handleSuccessfulLogin(username, password, socket);
      } else {
        socket.emit('errorMessage', json.msg);
      }
    })
    .catch(error => {
      console.error('Login error:', error);
      socket.emit('errorMessage', 'Unable to connect to server. Please try again.');
    });
}

function handleSuccessfulLogin(username, password, socket) {
  socket.emit('loggedIn', true);
  socket.emit('gameState', gameState);

  if (playerToSocket.has(username)) {
    playerToSocket.set(username, socket);
    socketToPlayer.set(socket, username);
    sendGameStateData(username, socket);
    return;
  }

  const gameStarted = gameState >= GameStates.PROMPTS;

  if (gameStarted || players.size >= 8) {
    socket.emit('loginResponse', 'audience');
    addNewAudience(username, socket);
  } else {
    addNewUser(username, password, socket);
  }

  sendGameStateData(username, socket);
}

function sendGameStateData(username, socket) {
  if (gameState === GameStates.VOTING) {
    sendVoteDataToPlayer(username, socket);
  } else if (gameState === GameStates.RESULTS) {
    sendResults();
  } else if (gameState === GameStates.SCORES || gameState === GameStates.GAME_OVER) {
    const playerScores = getPlayerScores();
    socket.emit('scores', Array.from(playerScores));
  }
}

function sendVoteDataToPlayer(username, socket) {
  const data = {};
  const playerAnswers = promptAllocation.get(currentVote);
  
  if (playerAnswers && playerAnswers[username] === undefined) {
    data.allowedToVote = true;
    data.vote = Object.values(playerAnswers);
    data.prompt = currentVote;
  } else {
    data.allowedToVote = false;
  }
  
  socket.emit('voteData', data);
}

function savePromptsToDatabase() {
  const unsavedPrompts = prompts.filter(p => !savedPromptTexts.has(p.text));

  console.log(`Saving ${unsavedPrompts.length} new prompts to database`);

  unsavedPrompts.forEach(prompt => {
    const username = prompt.user;
    const text = prompt.text;

    console.log(`Saving prompt from ${username}: "${text}"`);

    callAzureAPI('/prompt/create', 'post', {
      text,
      username,
      tags: []
    })
      .then(json => {
        if (json.result) {
          console.log(`Successfully saved prompt from ${username}`);
          savedPromptTexts.add(text);
        } else {
          console.error(`Failed to save prompt from ${username}: ${json.msg}`);
        }
      })
      .catch(error => {
        console.error(`Error saving prompt from ${username}:`, error);
      });
  });
}

function addNewAudience(username, socket) {
  audienceToSocket.set(username, socket);
  socketToAudience.set(socket, username);

  broadcastParticipants();
}

function addNewUser(username, password, socket) {
  if (players.size === 0) {
    console.log(`${username} is admin`);
    admin = username;
    socket.emit('loginResponse', 'admin');
    io.emit('adminAssigned', admin);
  }

  const playerData = {score: 0, password};
  socketToPlayer.set(socket, username);
  playerToSocket.set(username, socket);
  players.set(username, playerData);
  
  broadcastParticipants();
}

function resetGame() {
  console.log('Resetting game');
  
  for (const [player, sock] of playerToSocket.entries()) {
    if (sock && sock.connected) {
      sock.disconnect();
    }
  }
  
  players = new Map();
  playerToSocket = new Map();
  socketToPlayer = new Map();
  socketToAudience = new Map();
  audienceToSocket = new Map();
  admin = '';
  gameState = GameStates.JOINING;
  round = 0;
  prompts = [];
  promptAllocation = new Map();
  voteResults = new Map();
  usedPrompts = [];
  promptsForRound = [];
  promptsSubmitted = new Set();
  answersSubmitted = new Set();
  votesReceived = new Set();
  readyToVote = false;
  currentVote = '';
  savedPromptTexts = new Set();
  io.emit('adminAssigned', '');
  broadcastParticipants();
}

function startGame() {
  round = 1;
  gameNext();
}

function gameNext() {
  console.log(`Game advancing from state: ${gameState}`);
  
  switch(gameState) {
    case GameStates.JOINING:
      gameState = GameStates.PROMPTS;
      promptsSubmitted = new Set();
      io.emit('gameState', gameState);
      broadcastPromptStats();
      break;
      
    case GameStates.PROMPTS:
      promptAllocation = new Map();
      answersSubmitted = new Set();
      gameState = GameStates.ANSWERS;
      io.emit('gameState', gameState);
      sendPrompts();
      broadcastAnswerStats();
      break;
      
    case GameStates.ANSWERS:
      promptsForRound = Array.from(promptAllocation.keys());
      voteResults = new Map();
      gameState = GameStates.VOTING;
      gameNext();
      break;
      
    case GameStates.VOTING:
      io.emit('gameState', gameState);
      
      if (readyToVote) {
        sendResults();
        readyToVote = false;
      } else if (promptsForRound.length > 0) {
        currentVote = promptsForRound.pop();
        console.log(`Sending vote: ${currentVote}`);
        sendVotes(currentVote);
        readyToVote = true;
      } else {
        advanceToScores();
      }
      break;
      
    case GameStates.RESULTS:
      gameState = GameStates.VOTING;
      gameNext();
      break;
      
    case GameStates.SCORES:
      if (round > 3) {
        gameState = GameStates.GAME_OVER;
        io.emit('gameState', gameState);
      } else {
        io.emit('round', round);
        gameState = GameStates.PROMPTS;
        gameNext();
      }
      break;
  }
}

function advanceToScores() {
  round++;

  const playerScores = getPlayerScores();
  gameState = GameStates.SCORES;
  savePromptsToDatabase();

  io.emit('gameState', gameState);
  io.emit('scores', Array.from(playerScores));
  io.emit('displayScores', Array.from(playerScores));
}

async function sendPrompts() {
  const playerList = Array.from(players.keys());
  const numPlayers = playerList.length;
  if (numPlayers === 0) {
    console.warn('sendPrompts called with no players');
    return;
  }
  const promptsNeeded = (numPlayers % 2 === 0) ? (numPlayers / 2) : numPlayers;
  const numGamePrompts = Math.ceil(promptsNeeded / 2);
  const numApiPrompts = promptsNeeded - numGamePrompts;

  shuffleArray(prompts);
  const gamePromptsForRound = prompts
    .slice(0, numGamePrompts)
    .map(p => ({
      text: p.text,
      user: p.user
    }));

  let apiPromptsForRound = [];
  if (numApiPrompts > 0) {
    try {
      const response = await callAzureAPI('/utils/get', 'POST', {
        players: playerList,
        tag_list: []
      });


      const docs = Array.isArray(response) ? response : [];
      const mapped = docs.map(doc => {
        const texts = doc.texts || [];
        const english = texts.find(t => t.language === 'en') || texts[0];
        if (!english || !english.text) return null;

        return {
          text: english.text,
          user: doc.username || doc.player || 'unknown'
        };
      }).filter(Boolean);

      apiPromptsForRound = mapped.slice(0, numApiPrompts);
    } catch (err) {
      console.error('Error fetching prompts from /utils/get, falling back to game prompts only:', err);
      apiPromptsForRound = [];
    }
  }

  const promptsForRound = [...gamePromptsForRound, ...apiPromptsForRound];

  console.log(`Using ${promptsForRound.length} prompts this round (${gamePromptsForRound.length} from this game, ${apiPromptsForRound.length} from API)`);

  allocatePromptsToPlayers(promptsForRound);
}

function allocatePromptsToPlayers(promptsForRound) {
  const playerList = Array.from(players.keys());

  if (playerList.length < 2) {
    console.log('Not enough players to allocate prompts.');
    return;
  }

  const isEven = playerList.length % 2 === 0;

  const neededPrompts = isEven
    ? Math.floor(playerList.length / 2)
    : playerList.length;

  const pool = [...promptsForRound];

  promptAllocation = new Map();

  if (isEven) {
    allocatePromptsEven(playerList, pool, neededPrompts);
  } else {
    allocatePromptsOdd(playerList, pool, neededPrompts);
  }

  console.log(
    `Allocated ${promptAllocation.size} prompts for ${playerList.length} player(s).`
  );
}

function allocatePromptsEven(playerList, promptsPool, neededPrompts) {
  const playersToAssign = [...playerList];

  while (playersToAssign.length >= 2 && promptAllocation.size < neededPrompts) {
    const p1Index = Math.floor(Math.random() * playersToAssign.length);
    const player1 = playersToAssign.splice(p1Index, 1)[0];

    const p2Index = Math.floor(Math.random() * playersToAssign.length);
    const player2 = playersToAssign.splice(p2Index, 1)[0];

    const selectedPrompt = selectPrompt(promptsPool, player1, player2);
    assignPromptToPlayers(selectedPrompt, player1, player2);
  }
}

function allocatePromptsOdd(playerList, promptsPool, neededPrompts) {
  const n = playerList.length;
  if (n < 3) {
    return allocatePromptsEven(playerList, promptsPool, neededPrompts);
  }

  const ring = [...playerList];
  shuffleArray(ring);

  for (let i = 0; i < n && promptAllocation.size < neededPrompts; i++) {
    const player1 = ring[i];
    const player2 = ring[(i + 1) % n];

    const selectedPrompt = selectPrompt(promptsPool, player1, player2);
    assignPromptToPlayers(selectedPrompt, player1, player2);
  }
}

function selectPrompt(promptsForRound, player1, player2) {
  shuffleArray(promptsForRound);
  
  const solution = promptsForRound.find(p => 
    p.user !== player1 && 
    p.user !== player2 && 
    !usedPrompts.includes(p.text)
  );
  
  if (solution) {
    usedPrompts.push(solution.text);
    return solution.text;
  }
  
  const examplePrompts = [
  "The real reason the lecture recording 'failed' is...",
  "You know a group project is doomed when...",
  "The worst thing to say in a job interview is...",
  "A WiFi network name that should be illegal:",
  "The fastest way to fail a COMP3207 lab is to...",
  "My lecturer’s secret hobby is actually...",
  "The most cursed thing you could find in the lab fridge is...",
  "The university’s new slogan should be:",
  "The worst possible thing to hear on a Zoom call is...",
  "The mysterious email from \"IT Support\" actually said...",
  "The real reason the fire alarm keeps going off is...",
  "What you should *never* say to your project supervisor:",
  "The top-secret feature of the student portal is...",
  "The most chaotic thing to bring to a group presentation is...",
  "When the library closes, the printers secretly..."
];


  
  const selected = examplePrompts[Math.floor(Math.random() * examplePrompts.length)];
  usedPrompts.push(selected);
  return selected;
}

function assignPromptToPlayers(prompt, player1, player2) {
  const allocation = {};
  allocation[player1] = '';
  allocation[player2] = '';
  promptAllocation.set(prompt, allocation);
  
  playerToSocket.get(player1).emit('promptToAnswer', prompt);
  playerToSocket.get(player2).emit('promptToAnswer', prompt);
}

function getAnswerCounts() {
  const totalNeeded = promptAllocation.size * 2;
  let totalReceived = 0;

  for (const [prompt, answers] of promptAllocation.entries()) {
    for (const player in answers) {
      if (answers[player] && answers[player] !== '') {
        totalReceived++;
      }
    }
  }

  return { totalNeeded, totalReceived };
}

function submitPrompt(socket, promptText) {
  const playerUser = socketToPlayer.get(socket);
  const audienceUser = socketToAudience.get(socket);
  const user = playerUser || audienceUser;

  if (!user) {
    console.warn('submitPrompt called for unknown socket');
    socket.emit('errorMessage', 'You are not recognised as a player or audience member.');
    return;
  }

  prompts.push({ text: promptText, user });
  socket.emit('promptResponse', true);

  console.log(`Prompt submitted by ${user}. Total prompts this game: ${prompts.length}`);

  if (players.has(user)) {
    promptsSubmitted.add(user);
    console.log(
      `Players who have submitted at least one prompt: ${promptsSubmitted.size}/${players.size}`
    );
  }

  broadcastPromptStats();

  if (gameState === GameStates.PROMPTS && promptsSubmitted.size === players.size) {
    console.log('All players have submitted at least one prompt, auto-advancing');
    io.emit('allPromptsSubmitted', true);

    setTimeout(() => {
      if (gameState === GameStates.PROMPTS) {
        gameNext();
      }
    }, 1000);
  }
}

function submitAnswer(prompt, answer, socket) {
  const player = socketToPlayer.get(socket);

  if (!player) {
    console.warn('submitAnswer called for unknown socket');
    return;
  }

  const allocation = promptAllocation.get(prompt);

  if (!allocation) {
    console.warn(`submitAnswer: unknown prompt "${prompt}" for player ${player}`);
    return;
  }

  const isNewAnswer = !allocation[player];
  allocation[player] = answer;

  if (isNewAnswer) {
    answersSubmitted.add(player);
    console.log(
      `Answer submitted by ${player}. Total: ${answersSubmitted.size}/${players.size}`
    );
  } else {
    console.log(`Answer updated by ${player}`);
  }

  checkAllAnswersSubmitted();
}

function checkAllAnswersSubmitted() {
  const totalAnswersNeeded = promptAllocation.size * 2;
  let totalAnswersReceived = 0;

  for (const [prompt, answers] of promptAllocation.entries()) {
    for (const player in answers) {
      if (answers[player] && answers[player] !== '') {
        totalAnswersReceived++;
      }
    }
  }

  console.log(`Total answers: ${totalAnswersReceived}/${totalAnswersNeeded}`);

  if (totalAnswersReceived === totalAnswersNeeded) {
    console.log('All answers submitted, auto-advancing to voting');
    io.emit('allAnswersSubmitted', true);
    setTimeout(() => {
      if (gameState === GameStates.ANSWERS) {
        gameNext();
      }
    }, 1000);
  }
}

function sendVotes(promptForVoting) {
  const allocation = promptAllocation.get(promptForVoting);
  if (!allocation) {
    console.warn(`No allocation found for prompt "${promptForVoting}"`);
    return;
  }

  const entries = Object.entries(allocation);

  let answers = entries.map(([_, ans]) =>
    typeof ans === 'string' ? ans : ''
  );

  while (answers.length < 2) {
    answers.push('');
  }

  const [option1, option2] = answers;

  const voteData = {
    [option1]: 0,
    [option2]: 0
  };
  voteResults.set(promptForVoting, voteData);
  votesReceived = new Set();

  const votersMap = {
    [option1]: [],
    [option2]: []
  };
  voteVoters.set(promptForVoting, votersMap);

  for (const player of players.keys()) {
    const socket = playerToSocket.get(player);
    if (!socket) continue;

    const data = {};
    if (allocation[player] === undefined) {
      data.allowedToVote = true;
      data.vote = answers;
      data.prompt = promptForVoting;
    } else {
      data.allowedToVote = false;
    }

    socket.emit('voteData', data);
  }

  for (const [audName, socket] of audienceToSocket.entries()) {
    if (!socket) continue;

    socket.emit('voteData', {
      allowedToVote: true,
      vote: answers,
      prompt: promptForVoting
    });
  }

  io.emit('displayAns', {
    prompt: promptForVoting,
    ans1: option1 || '(no answer)',
    ans2: option2 || '(no answer)'
  });

  broadcastVoteStats();
}

function handleVote(socket, data) {
  const voter =
    socketToPlayer.get(socket) ||
    socketToAudience.get(socket);

  if (!voter) {
    console.warn('Vote from unknown socket, ignoring');
    return;
  }

  const resultsForPrompt = voteResults.get(data.prompt);
  const allocation = promptAllocation.get(data.prompt);

  if (!resultsForPrompt || !allocation) {
    console.warn(`Vote received for unknown prompt "${data.prompt}" from ${voter}`);
    return;
  }

  if (votesReceived.has(voter)) {
    console.log(`Ignoring duplicate vote from ${voter}`);
    return;
  }

  if (typeof resultsForPrompt[data.answer] !== 'number') {
    console.warn(`Invalid answer option "${data.answer}" from ${voter}`);
    return;
  }

  resultsForPrompt[data.answer]++;
  votesReceived.add(voter);

  const votersForPrompt = voteVoters.get(data.prompt);
  if (votersForPrompt && votersForPrompt[data.answer]) {
    votersForPrompt[data.answer].push(voter);
  }

  broadcastVoteStats();

  console.log(`Vote received from ${voter}. Total votes: ${votesReceived.size}`);

  const playersWhoAnswered = Object.keys(allocation);
  const eligibleVoters =
    players.size + audienceToSocket.size - playersWhoAnswered.length;

  console.log(
    `Expected voters: ${eligibleVoters} (${players.size} players + ${audienceToSocket.size} audience - ${playersWhoAnswered.length} answerers)`
  );

  if (eligibleVoters > 0 && votesReceived.size >= eligibleVoters) {
    console.log('All votes received, auto-advancing to results');
    setTimeout(() => {
      if (gameState === GameStates.VOTING && readyToVote) {
        gameNext();
      }
    }, 1000);
  }
}

function sendResults() {
  const result = voteResults.get(currentVote);
  const votersForPrompt = voteVoters.get(currentVote) || {};
  const data = {
    prompt: currentVote,
    voteResults: []
  };

  const userToPrompt = promptAllocation.get(currentVote) || {};

  for (const answer of Object.keys(result)) {
    const user = Object.keys(userToPrompt).find(
      usr => userToPrompt[usr] === answer
    );
    const numVotes = result[answer];
    const voterList = votersForPrompt[answer] || [];

    data.voteResults.push({
      text: answer,
      user,
      votes: numVotes,
      voters: voterList
    });

    if (players.has(user)) {
      players.get(user).score += numVotes * round * 100;
    }
  }

  gameState = GameStates.RESULTS;
  io.emit('gameState', gameState);
  io.emit('voteResults', data);
  io.emit('displayRes', data);
}

function shuffleArray(array) {
  for (let i = array.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [array[i], array[j]] = [array[j], array[i]];
  }
}

function getPlayerScores() {
  const scores = new Map();
  for (const [player, data] of players.entries()) {
    scores.set(player, data.score);
  }
  return scores;
}

function broadcastAnswerStats() {
  const answered = Array.from(answersSubmitted);
  const allPlayers = Array.from(players.keys());
  const waiting = allPlayers.filter(p => !answersSubmitted.has(p));

  io.emit('answerStats', {
    answered,
    waiting
  });
}

function broadcastVoteStats() {
  if (!currentVote || !promptAllocation.has(currentVote)) {
    return;
  }
  const voted = Array.from(votesReceived);
  const allocation = promptAllocation.get(currentVote) || {};
  const playersWhoAnsweredThisPrompt = new Set(Object.keys(allocation));
  const allPlayers = Array.from(players.keys());
  const allAudience = Array.from(audienceToSocket.keys());

  const eligibleVoters = allPlayers
    .filter(p => !playersWhoAnsweredThisPrompt.has(p))
    .concat(allAudience);

  const waiting = eligibleVoters.filter(name => !votesReceived.has(name));

  io.emit('voteStats', {
    voted,
    waiting
  });
}

function broadcastParticipants() {
  const playersList = Array.from(players.keys());
  const audienceList = Array.from(audienceToSocket.keys());

  io.emit('updatedPlayers', {
    players: playersList,
    audience: audienceList
  });
}

function broadcastPromptStats() {
  const totalPrompts = prompts.length;
  const authors = prompts
    .map(p => p.user)
    .filter(u => typeof u === 'string' && u.length > 0);

  const uniqueAuthors = Array.from(new Set(authors));

  io.emit('promptStats', {
    count: totalPrompts,
    authors: uniqueAuthors
  });
}


io.on('connection', socket => { 
  console.log('New connection');

  socket.on('register', data => {
    if (socketToPlayer.has(socket)) return;
    registerUser(data.user, data.pwd, socket);
  });

  socket.on('login', data => {
    loginUser(data.user, data.pwd, socket);
  });

  socket.on('userPrompt', data => {
    submitPrompt(socket, data.prompt);
  });

  socket.on('userAnswer', data => {
    submitAnswer(data.prompt, data.answer, socket);
  });

  socket.on('vote', data => {
    handleVote(socket, data);
  });

  socket.on('admin', data => {
    const isAdmin = playerToSocket.get(admin) === socket;
    const canReset = data === 'reset' && gameState === GameStates.GAME_OVER;
    
    if (isAdmin) {
      if (data === 'start' && gameState === GameStates.JOINING) {
        startGame();
      } else if (data === 'next') {

        if (gameState === GameStates.ANSWERS) {
          const { totalNeeded, totalReceived } = getAnswerCounts();

          if (totalReceived < totalNeeded) {
            console.log(
              `Admin tried to advance early in ANSWERS: ${totalReceived}/${totalNeeded} answers`
            );
            socket.emit(
              'errorMessage',
              `Not all answers submitted yet (${totalReceived}/${totalNeeded}).`
            );
            return;
          }
        }


        gameNext();
      } else if (data === 'reset') {
        resetGame();
      }
    } else if (canReset) {
      resetGame();
    } else {
      console.log('Non-admin tried to access admin features');
    }
  });

  socket.on('disconnect', () => {
    console.log('Dropped connection');
    
    const disconnectedPlayer = socketToPlayer.get(socket);
    
    if (disconnectedPlayer === admin) {
      console.log('Admin disconnected, resetting game');
      resetGame();
    } else if (disconnectedPlayer) {
      socketToPlayer.delete(socket);
      playerToSocket.delete(disconnectedPlayer);
      console.log(`Player ${disconnectedPlayer} removed from game`);
    }
    
    const disconnectedAudience = socketToAudience.get(socket);
    if (disconnectedAudience) {
      socketToAudience.delete(socket);
      audienceToSocket.delete(disconnectedAudience);
      console.log(`Audience member ${disconnectedAudience} removed`);
    }

    broadcastParticipants();
  });
});

function startServer() {
  const PORT = process.env.PORT || 8080;
  server.listen(PORT, () => {
    console.log(`Server listening on port ${PORT}`);
  });
}

if (module === require.main) {
  startServer();
}

module.exports = server;