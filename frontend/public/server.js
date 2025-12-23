// let http = require('http');

// http.createServer(function (req, res) {
//     res.writeHead(200, {'Content-Type': 'text/plain'});
//     res.end('Hello World!');
// }).listen(8080);

var socket = null;

var app = new Vue({
    el: '#server',
    data: {
        loggedIn: false,
        scene: 0,
        inputUsername: '',
        inputPassword: '',
        isAdmin: false,

        statusMessage: '',
        statusColor: 'red',

        item: '',
        amount: 0,
        payer: '',
        expenses: [{ description: 'Office Chair', amount: 150, payer: 'Alice', date: '2024-06-01' },
        { description: 'Monitor', amount: 350, payer: 'Bob', date: '2024-06-01' }
        ]
    },
    mounted() {
        if (localStorage.getItem('loggedIn') === 'true') {
            this.inputUsername = localStorage.getItem('username');
            this.loggedIn = true;
        }
        if(this.inputUsername === 'test'){
            this.isAdmin = true;
        }
    },
    computed: {

    },
    methods: {
        async request(endpoint) {
            try {
                const response = await fetch(endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username: this.inputUsername, password: this.inputPassword })
                });
                const data = await response.json();
                if (endpoint === '/login') {
                    if (data.success) {
                        localStorage.setItem('username', this.inputUsername);
                        localStorage.setItem('loggedIn', 'true');
                        this.loggedIn = true;
                        this.scene = 1;
                    } else {
                        this.statusMessage = data.message;
                        this.statusColor = 'red';
                    }
                } else {
                    this.statusMessage = data.message;
                    this.statusColor = 'green';
                }
                console.log(endpoint + " request sent from " + this.inputUsername);
            } catch (error) {
                console.error('Error:', error);
            }
        },
        login() { this.request('/login'); },
        register() { this.request('/register'); },
        logout() {
            localStorage.clear();

            this.loggedIn = false;
            this.inputUsername = '';

            window.location.href = '/display'; 
            console.log("User logged out + " + this.inputUsername);
        },
        newExpense() {
            this.expenses.push({ description: this.item, amount: this.amount, payer: this.payer, date: new Date().toISOString().split('T')[0] });
            // this will clear the form inputs
            this.item = '';
            this.amount = 0;
            this.payer = '';
        }

    }
});