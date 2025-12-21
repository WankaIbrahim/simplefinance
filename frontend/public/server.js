// let http = require('http');

// http.createServer(function (req, res) {
//     res.writeHead(200, {'Content-Type': 'text/plain'});
//     res.end('Hello World!');
// }).listen(8080);

var socket = null;

var app = new Vue({
    el: '#server',
    data: {
        loggedIn:false,
        inputUsername: '',
        inputPassword: '',
    },

    computed: {

    },
    methods:{
        async request(endpoint) {
            this.statusMessage = "Processing...";
            try {

                this.loggedIn = true;
                console.log(endpoint + " request sent from " + this.inputUsername);
            } catch (error) {
                console.error('Error:', error);
            }
        },
        login() { this.request('/login'); },
        register() { this.request('/register'); },

    }
});