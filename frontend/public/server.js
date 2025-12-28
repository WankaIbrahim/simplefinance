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

        activeGroupIndex: 0,
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
                        localStorage.setItem('username', data.username);
                        localStorage.setItem('userId', data.userId);     
                        localStorage.setItem('loggedIn', 'true');

                        this.inputUsername = data.username;
                        this.userId = data.userId;
                        this.loggedIn = true;

                        if (window.location.pathname === '/display') {
                            this.fetchMyGroups();
                            this.fetchMembershipGroups();
                        }
                    } else {
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
        async newExpense() {
        if (!this.item || !this.price) {
            alert('Please fill in item name and price');
            return;
        }

        const newItem = {
            name: this.item,
            quantity: this.quantity || 1,
            price: parseFloat(this.price),
            buyer: this.payer ? { username: this.payer } : null,
            purchased: false,
            voted: []
        };

        try {
            const response = await fetch('/add-item', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    groupId: this.activeGroup.groupId,
                    item: newItem
                })
            });
            const data = await response.json();

            if (data.result) {
                await this.fetchGroupDetails(this.activeGroup.groupId);
                
                // Clear form
                this.item = '';
                this.quantity = 1;
                this.payer = '';
                this.price = 0.0;
            } else {
                alert('Failed to add item: ' + data.msg);
            }
        } catch (error) {
            console.error('Error adding item:', error);
            alert('Failed to add item');
        }
    },
    async removeExpense(itemId) {
        if (!confirm('Are you sure you want to remove this item?')) return;

        try {
            const response = await fetch('/remove-item', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    groupId: this.activeGroup.groupId,
                    itemId: itemId
                })
            });
            const data = await response.json();

            if (data.result) {
                await this.fetchGroupDetails(this.activeGroup.groupId);
            } else {
                alert('Failed to remove item: ' + data.msg);
            }
        } catch (error) {
            console.error('Error removing item:', error);
            alert('Failed to remove item');
        }
    },

    async updateExpense(itemId, updates) {
        try {
            const response = await fetch('/update-item', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    groupId: this.activeGroup.groupId,
                    itemId: itemId,
                    updates: updates
                })
            });
            const data = await response.json();

            if (data.result) {
                await this.fetchGroupDetails(this.activeGroup.groupId);
            } else {
                alert('Failed to update item: ' + data.msg);
            }
        } catch (error) {
            console.error('Error updating item:', error);
            alert('Failed to update item');
        }
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

        async fetchUserProfile(id) {
            try {
                const response = await fetch('/get-user-details', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ userId: id })
                });
                const data = await response.json();

                if (data.result && data.user) {
                    this.searchUsername = data.user.username;
                    this.searchUserId = data.user.id;
                }
            } catch (error) {
                console.error("Error loading profile:", error);
            }
        },
        async upvote(item) {
        try {
            const response = await fetch('/vote-item', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    groupId: this.activeGroup.groupId,
                    itemId: item.id,
                    username: this.inputUsername,
                    action: 'upvote'
                })
            });
            const data = await response.json();

            if (data.result) {
                await this.fetchGroupDetails(this.activeGroup.groupId);
            }
        } catch (error) {
            console.error('Error upvoting:', error);
        }
    },
    
    async downvote(item) {
        try {
            const response = await fetch('/vote-item', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    groupId: this.activeGroup.groupId,
                    itemId: item.id,
                    username: this.inputUsername,
                    action: 'downvote'
                })
            });
            const data = await response.json();

            if (data.result) {
                await this.fetchGroupDetails(this.activeGroup.groupId);
            }
        } catch (error) {
            console.error('Error downvoting:', error);
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