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

        activeGroupIndex: 0, // Id of current group
        sortBy: 'votes',
        sortDesc: true,

        userId: null,
        users: [{ id: 1, username: 'Alice' },
        { id: 2, username: 'Bob' },
        { id: 3, username: 'Dave' },
        { id: 4, username: 'test' }],
        searchUseraname: '',
        searchUserId: null,
        groupNotFound: false,

        activeGroup: null,
        groups: [
            {
                id: 101,
                owner: "Bob",
                name: "Office Furniture 1",
                members: ["Alice", "Bob", "test"],
                items: [
                    {
                        id: 1,
                        name: "Ergonomic Chairs",
                        quantity: 4,
                        price: 150.00,
                        buyer: "Alice",
                        votedBy: [],
                        purchased: false
                    },
                    {
                        id: 2,
                        name: "Standing Desk",
                        quantity: 1,
                        price: 450.00,
                        buyer: "Bob",
                        votedBy: [],
                        purchased: true // This one is already bought
                    }
                ]
            },
            {
                id: 102,
                admin: "Bob",
                name: "Office Furniture 2",
                members: ["Alice", "Bob", "test"],
                items: [
                    {
                        id: 1,
                        name: "Ergonomic Chairs",
                        quantity: 4,
                        price: 150.00,
                        buyer: "Alice",
                        votedBy: [],
                        purchased: false
                    },
                    {
                        id: 2,
                        name: "Standing Desk",
                        quantity: 1,
                        price: 450.00,
                        buyer: "Bob",
                        votedBy: [],
                        purchased: true // This one is already bought
                    }
                ]
            },
            {
                id: 103,
                admin: "test",
                name: "Kitchen Supplies (test)",
                members: ["Alice", "Dave"],
                items: [
                    {
                        id: 3,
                        name: "Coffee Machine",
                        quantity: 1,
                        price: 80.00,
                        buyer: "Dave",
                        votedBy: [],
                        purchased: false
                    }
                ]
            },
            {
                id: 104,
                admin: "test",
                name: "Kitchen Supplies (test 2)",
                members: ["Alice", "Dave"],
                items: [
                    {
                        id: 3,
                        name: "Coffee Machine",
                        quantity: 1,
                        price: 80.00,
                        buyer: "Dave",
                        votedBy: [],
                        purchased: false
                    }
                ]
            }
        ],
        item: '',
        quantity: 0,
        payer: '',
        price: 0.0,
        groupDescription: '',


        showExpenseModal: false,
        lightTheme: false
    },
    mounted() {
        if (localStorage.getItem('loggedIn') === 'true') {
            this.inputUsername = localStorage.getItem('username');
            this.userId = this.users.find(user => user.username === this.inputUsername)?.id || null;
            this.loggedIn = true;
        }
        if (this.inputUsername === 'test') {
            this.isAdmin = true;
        }
        const urlParams = new URLSearchParams(window.location.search);
        const groupId = urlParams.get('id');
        if (groupId) {
            // groupId is a string, g.id is a number
            const foundGroup = this.groups.find(g => g.id == groupId);

            if (foundGroup) {
                this.activeGroup = foundGroup;
                this.groupNotFound = false;
            } else {
                this.groupNotFound = true;
            }
        } else {
            this.groupNotFound = true;
        }

        const profileID = urlParams.get('username');
        if (profileID) {
            this.searchUsername = profileID;
            this.searchUserId = this.users.find(user => user.username === this.searchUsername)?.id || null;
        }
    },
    computed: {
        myGroups() {
            return this.groups.filter(group => {
                return group.admin === this.inputUsername;
            });
        },
        membershipGroups() {
            return this.groups.filter(group => {
                return group.members.includes(this.inputUsername);
            });
        }
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
        login() {
            this.request('/login');
        },
        register() { this.request('/register'); },
        logout() {
            localStorage.clear();

            this.loggedIn = false;
            this.inputUsername = '';

            window.location.href = '/display';
            console.log("User logged out + " + this.inputUsername);
        },
        newExpense() {

            this.activeGroup.items.push(
                {
                    id: 3,
                    name: this.item,
                    quantity: this.quantity,
                    price: this.price,
                    buyer: this.payer,
                    votedBy: [],
                    purchased: false
                }
            );

            // this will clear the form inputs
            this.item = '';
            this.quantity = 0;
            this.payer = '';
            this.price = 0.0;
        },
        upvote(item) {
            if (!item.votedBy.includes(this.inputUsername)) {
                item.votedBy.push(this.inputUsername);
                item.votes = item.votedBy.length;
            }
        },
        downvote(item) {
            const index = item.votedBy.indexOf(this.inputUsername);
            if (index !== -1) {
                item.votedBy.splice(index, 1);
                item.votes = item.votedBy.length;
            }
        },
        toggleTheme() {
            this.lightTheme = !this.lightTheme;
        }
    }
});