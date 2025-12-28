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
        searchUsername: '',
        searchUserId: null,
        groupNotFound: false,

        activeGroup: null,
        groups: [],
        groupMembers: [],
        item: '',
        quantity: 0,
        payer: '',
        price: 0.0,
        groupDescription: '',


        showExpenseModal: false,
        lightTheme: false,
    },
    mounted() {
        if (localStorage.getItem('loggedIn') === 'true') {
            this.inputUsername = localStorage.getItem('username');
            this.userId = localStorage.getItem('userId');
            this.loggedIn = true;
            if (window.location.pathname === '/display' || window.location.pathname === '/') {
                this.fetchMyGroups();
                this.fetchMembershipGroups();
            }
        }

        const urlParams = new URLSearchParams(window.location.search);

        // load a group view
        const groupId = urlParams.get('groupId');
        if (groupId) {
            this.fetchGroupDetails(groupId);
        }

        // load a profile view
        const profileId = urlParams.get('userId');
        if (profileId) {
            this.fetchUserProfile(profileId);
        } else if (window.location.pathname === '/profile' && this.userId) {
            // If on profile page but no ID in URL, load MY profile
            this.fetchUserProfile(this.userId);
        }


    },
    computed: {
        myGroups() {
            return this.groups.filter(group => {
                if (group.admins && Array.isArray(group.admins)) {
                    return group.admins.some(admin => admin.username === this.inputUsername);
                }
                return false;
            });
        },

        membershipGroups() {
            return this.groups.filter(group => {
                const inUsers = group.users && Array.isArray(group.users) &&
                    group.users.some(u => u.username === this.inputUsername);

                // const inGuests = group.guests && Array.isArray(group.guests) &&
                //     group.guests.some(g => g.username === this.inputUsername);

                if (inUsers) return true;

                return false;
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

                if (data.result === true) {
                    if (endpoint === '/login') {
                        localStorage.setItem('username', data.username); // Use server data
                        localStorage.setItem('userId', data.userId);     // SAVE ID HERE
                        localStorage.setItem('loggedIn', 'true');

                        this.inputUsername = data.username;
                        this.userId = data.userId;
                        this.loggedIn = true;

                        // Redirect to home if needed, or fetch data
                        if (window.location.pathname === '/display') {
                            this.fetchMyGroups();
                            this.fetchMembershipGroups();
                        }
                    } else {
                        // Register logic...
                        this.statusMessage = 'Registration successful';
                        this.statusColor = 'green';
                    }
                } else {
                    this.statusMessage = data.msg;
                    this.statusColor = 'red';
                }
            } catch (error) {
                console.error('Error:', error);
                this.statusMessage = 'Connection failed';
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
        async fetchGroupDetails(id) {
            try {
                const response = await fetch('/get-group-details', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ groupId: id })
                });
                const data = await response.json();

                if (data.result && data.group) {
                    this.activeGroup = data.group;
                    this.groupNotFound = false;
                } else {
                    this.groupNotFound = true;
                }
            } catch (error) {
                console.error("Error loading group:", error);
                this.groupNotFound = true;
            }
        },

        // NEW: Fetch user profile details
        async fetchUserProfile(id) {
            try {
                const response = await fetch('/get-user-details', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ userId: id })
                });
                const data = await response.json();

                if (data.result && data.user) {
                    // You might want a new data property for 'viewedProfile' 
                    // instead of overwriting 'users' array
                    this.searchUsername = data.user.username;
                    this.searchUserId = data.user.id;
                    // Store the full object if you want to display email/bio
                    // this.viewedProfile = data.user; 
                }
            } catch (error) {
                console.error("Error loading profile:", error);
            }
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
        },
        async fetchMyGroups() {
            if (!this.inputUsername) return;

            try {
                const response = await fetch('/my-groups', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username: this.inputUsername })
                });
                const data = await response.json();

                if (data.result && data.groups) {
                    data.groups.forEach(serverGroup => {
                        const exists = this.groups.find(g => g.id === serverGroup.id);
                        if (!exists) {
                            this.groups.push(serverGroup);
                        }
                    });
                }
                // console.log(groups + " fetched for user " + this.inputUsername);
            } catch (error) {
                console.error("Error fetching groups:", error);
            }
        },
        //
        //
        async fetchMembershipGroups() {
            if (!this.inputUsername) return;
            try {
                const response = await fetch('/membership-groups', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username: this.inputUsername })
                });
                const data = await response.json();

                if (data.result && data.groups) {
                    data.groups.forEach(serverGroup => {
                        // FIX: Check against the main 'groups' array, not the computed property
                        const exists = this.groups.find(g => g.id === serverGroup.id);
                        if (!exists) {
                            this.groups.push(serverGroup);
                        }
                    });
                }
            } catch (error) {
                console.error("Error fetching groups:", error);
            }
        },
    }
});