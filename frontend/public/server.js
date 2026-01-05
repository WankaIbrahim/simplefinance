var socket = null;

var app = new Vue({
    el: '#server',
    data: {

        // User authentication data
        loggedIn: false,
        inputUsername: '',
        inputPassword: '',
        userId: null,
        isAdmin: false,

        // Data to update user
        newPassword: '',
        inputEmail: '',

        // Status message for login/register
        statusMessage: '',
        statusColor: 'red',

        // Data for profile view
        searchUsername: '',
        searchUserId: null,

        // Profile picture
        searchUserPfp: '',
        pfpFile: null,
        pfpStatus: '',

        // Bio
        searchUserBio: '',
        bioDraft: '',
        bioStatus: '',
        bioSaving: false,

        // Data for group view
        groupNotFound: false,
        activeGroup: null,
        // data for sorting the group table
        sortBy: 'votes',
        sortDesc: true,

        // Data for groups
        groups: [],
        groupMembers: [],
        item: '',
        quantity: 0,
        payer: '',
        url: '',
        price: 0.0,
        groupDescription: '',

        // Misc data 
        showExpenseModal: false,
        lightTheme: false,
        mobileMenuOpen: false,
        leftSidebarOpen: false,
        rightSidebarOpen: false,
        touchStartX: 0,
        touchEndX: 0,
        windowWidth: window.innerWidth,

        // friend logic
        friends: [],
        incomingRequests: [],
        outgoingRequests: [],

        // group creation logic
        showCreateGroupModal: false,

        newGroup: {
            name: '',
            description: '',
            budget: 0
        },
        showInviteModal: false,
        inviteIdentifier: '',
        inviteSending: false,
        inviteStatusMessage: '',
        inviteStatusColor: 'red',


        // find users to add to a group
        memberSearchQuery: '',
        memberSearchResults: [],
        searchLoading: false,
        activeSearchRole: 'users',

        showRemoveConfirm: false,
        showEditExpenseModal: false,
        selectedExpense: null,

        editExpenseData: {
            id: null,
            name: '',
            price: 0,
            quantity: 1,
            buyerUsername: '',
            url: ''
        },


        // Lists of selected people
        selectedAdmins: [],
        selectedUsers: [],
        selectedGuests: [],

        showGroupSettingsModal: false,
        editGroupData: {
            name: '',
            description: '',
            budget: 0
        },

        // Ai modal states
        showAiModal: false,
        aiLoading: false,
        aiData: {
            idea: '',
            people: 5,
            budget: 0,
            notes: ''
        },
        
        // Ai suggested items
        newGroupItems: []
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
        this.fetchMyData();

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

        // swipe menus functionality
        window.addEventListener('resize', this.handleResize);
        window.addEventListener('touchstart', e => {
            this.touchStartX = e.changedTouches[0].screenX;
        });
        window.addEventListener('touchend', e => {
            this.touchEndX = e.changedTouches[0].screenX;
            this.handleSwipe();
        });

        if (window.location.pathname === '/settings' && this.userId) {
            this.fetchUserProfile(this.userId);
        }


    },
    beforeDestroy() {
        window.removeEventListener('resize', this.handleResize);
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
        sortedGroupItems() {
            if (!this.activeGroup || !Array.isArray(this.activeGroup.items)) return [];
            const items = [...this.activeGroup.items];

            return items.sort((a, b) => {
                const ap = a.priority ? 1 : 0;
                const bp = b.priority ? 1 : 0;

                if (bp !== ap) return bp - ap;

                const ar = a.priorityRank || 0;
                const br = b.priorityRank || 0;
                return ar - br;
            });
        },



        membershipGroups() {
            return this.groups.filter(group => {
                const inUsers = group.users && Array.isArray(group.users) &&
                    group.users.some(u => u.username === this.inputUsername);
                if (inUsers) return true;

                return false;
            });
        },

        isCurrentUserAdmin() {
            if (!this.activeGroup || !this.activeGroup.admins) return false;
            return this.activeGroup.admins.some(admin => admin.username === this.inputUsername);
        },

        isCurrentUserMember() {
            if (!this.activeGroup || !this.activeGroup.users) return false;
            return this.activeGroup.users.some(user => user.username === this.inputUsername);
        },

        isCurrentUserGuest() {
            if (!this.activeGroup || !this.activeGroup.guests) return false;
            return this.activeGroup.guests.some(guest => guest.username === this.inputUsername);
        },

        isCurrentUserInGroup() {
            return this.isCurrentUserAdmin || this.isCurrentUserMember || this.isCurrentUserGuest;
        },
        // currentPath() {
        // return window.location.pathname;
        // }
        onlineFriends() {
            return this.friends;
        },

        isFriend() {
            return this.friends && this.friends.includes(this.searchUsername);
        },
        hasSentRequest() {
            return this.outgoingRequests && this.outgoingRequests.includes(this.searchUsername);
        },
        hasReceivedRequest() {
            return this.incomingRequests && this.incomingRequests.includes(this.searchUsername);
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
                } w
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

            let buyerObj = null;
            if (this.payer) {
                
                const allMembers = [
                    ...(this.activeGroup.admins || []),
                    ...(this.activeGroup.users || []),
                    ...(this.activeGroup.guests || [])
                ];
                const foundUser = allMembers.find(u => u.username === this.payer);
                
                if (foundUser) {
                    buyerObj = { username: foundUser.username, id: foundUser.id };
                }
            }

            const newItem = {
                name: this.item,
                quantity: this.quantity || 1,
                price: parseFloat(this.price),
                url: this.url,
                buyer: buyerObj,
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
                    this.url = '';
                    this.buyer = '';
                } else {
                    alert('Failed to add item: ' + data.msg);
                    this.item = '';
                    this.quantity = 1;
                    this.payer = '';
                    this.price = 0.0;
                    this.url = '';
                    this.buyer = '';
                }
            } catch (error) {
                console.error('Error adding item:', error);
                alert('Failed to add item');
                this.item = '';
                    this.quantity = 1;
                    this.payer = '';
                    this.price = 0.0;
                    this.url = '';
                    this.buyer = '';
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
                    this.searchUserPfp = data.user.pfpUrl || '';
                    this.inputEmail = data.user.email || '';
                    this.searchUserBio = data.user.bio || '';
                    this.bioDraft = this.searchUserBio;
                }
            } catch (error) {
                console.error("Error loading profile:", error);
            }
        },

        async saveBio() {
            if (!this.userId || this.searchUserId != this.userId) return;

            try {
                this.bioSaving = true;
                this.bioStatus = "";

                const response = await fetch('/update-user', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        userId: this.userId,
                        updates: {
                            bio: this.bioDraft
                        }
                    })
                });

                const data = await response.json();

                if (data.result) {
                    this.searchUserBio = this.bioDraft;
                    this.bioStatus = "Saved!";
                } else {
                    this.bioStatus = data.msg || "Failed to save bio";
                }
            } catch (error) {
                console.error("Error saving bio:", error);
                this.bioStatus = "Failed to save bio";
            } finally {
                this.bioSaving = false;
                setTimeout(() => { this.bioStatus = ""; }, 2000);
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


        onPfpSelected(e) {
            const file = e.target.files && e.target.files[0];
            if (!file) return;

            const okTypes = ["image/jpeg", "image/png", "image/webp"];
            if (!okTypes.includes(file.type)) {
                this.pfpStatus = "Please upload JPG, PNG, or WEBP.";
                this.pfpFile = null;
                e.target.value = "";
                return;
            }

            if (file.size > 2 * 1024 * 1024) {
                this.pfpStatus = "Max file size is 2MB.";
                this.pfpFile = null;
                e.target.value = "";
                return;
            }

            this.pfpFile = file;
            this.pfpStatus = `Selected: ${file.name}`;
        },
        openInviteModal() {
            this.showInviteModal = true;
            this.inviteIdentifier = '';
            this.inviteStatusMessage = '';
            this.inviteStatusColor = 'red';
        },

        closeInviteModal() {
            this.showInviteModal = false;
        },

        async sendInvite() {
            if (!this.inviteIdentifier || this.inviteSending) return;

            if (!this.activeGroup || !this.activeGroup.groupId) {
                this.inviteStatusMessage = "Group not loaded.";
                this.inviteStatusColor = "red";
                return;
            }

            if (!this.isCurrentUserAdmin) {
                this.inviteStatusMessage = "Only admins can invite members.";
                this.inviteStatusColor = "red";
                return;
            }

            this.inviteSending = true;
            this.inviteStatusMessage = '';
            this.inviteStatusColor = 'red';

            try {
                const response = await fetch('/group/invite', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        groupId: this.activeGroup.groupId,
                        identifier: this.inviteIdentifier,
                        inviterId: this.userId,
                        inviterUsername: this.inputUsername
                    })
                });

                const data = await response.json().catch(() => ({}));

                if (!response.ok || data.result === false) {
                    throw new Error(data.msg || "Invite failed");
                }

                this.inviteStatusMessage = data.msg || "Invite sent!";
                this.inviteStatusColor = "green";

                await this.fetchGroupDetails(this.activeGroup.groupId);

                setTimeout(() => this.closeInviteModal(), 700);
            } catch (err) {
                this.inviteStatusMessage = err.message || "Something went wrong";
                this.inviteStatusColor = "red";
            } finally {
                this.inviteSending = false;
            }
        },


        async uploadPfp() {
            if (!this.pfpFile) return;
            if (!this.userId) {
                this.pfpStatus = "You must be logged in.";
                return;
            }

            try {
                this.pfpStatus = "Uploading...";
                const form = new FormData();
                form.append("pfp", this.pfpFile);
                form.append("userId", this.userId);

                const uploadRes = await fetch("/upload-pfp", {
                    method: "POST",
                    body: form
                });

                const uploadData = await uploadRes.json();
                if (!uploadRes.ok || !uploadData.result) {
                    throw new Error(uploadData.msg || "Upload failed");
                }

                const pfpUrl = uploadData.pfpUrl;

                const updateRes = await fetch("/update-user", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        userId: this.userId,
                        updates: { pfpUrl }
                    })
                });

                const updateData = await updateRes.json();
                if (!updateData.result) {
                    throw new Error(updateData.msg || "Failed to save profile picture");
                }

                this.searchUserPfp = pfpUrl;
                this.pfpFile = null;
                this.pfpStatus = "Profile picture updated!";
            } catch (err) {
                console.error("PFP upload error:", err);
                this.pfpStatus = err.message || "Failed to update profile picture";
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
        handleSwipe() {
            const distance = this.touchEndX - this.touchStartX;
            const threshold = 50;
            const edgeZone = 50;

            // Swipe RIGHT (Open Left Sidebar)
            if (distance > threshold && this.touchStartX < edgeZone) {
                this.leftSidebarOpen = true;
            }
            // Swipe LEFT (Close Left Sidebar if open)
            else if (distance < -threshold && this.leftSidebarOpen) {
                this.leftSidebarOpen = false;
            }

            // Swipe LEFT (Open Right Sidebar)
            if (distance < -threshold && this.touchStartX > window.innerWidth - edgeZone) {
                this.rightSidebarOpen = true;
            }
            // Swipe RIGHT (Close Right Sidebar if open)
            else if (distance > threshold && this.rightSidebarOpen) {
                this.rightSidebarOpen = false;
            }
        },
        handleResize() {
            this.windowWidth = window.innerWidth;
        },


        closeSidebars() {
            this.leftSidebarOpen = false;
            this.rightSidebarOpen = false;
            this.mobileMenuOpen = false;
        },
        async updateProfile() {
            if (!this.userId) {
                this.statusMessage = "You must be logged in";
                this.statusColor = "red";
                return;
            }

            try {
                const updates = {};

                if (this.newPassword && this.newPassword.trim().length > 0) {
                    updates.password = this.newPassword.trim();
                }

                if (this.inputEmail && this.inputEmail.trim().length > 0) {
                    updates.email = this.inputEmail.trim();
                }

                if (this.inputUsername && this.inputUsername.trim().length > 0) {
                    updates.username = this.inputUsername.trim();
                }

                if (Object.keys(updates).length === 0) {
                    this.statusMessage = "Nothing to update";
                    this.statusColor = "red";
                    return;
                }

                const response = await fetch('/update-user', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        userId: this.userId,
                        updates
                    })
                });

                const data = await response.json();

                if (data.result) {
                    this.statusMessage = "Updated successfully";
                    this.statusColor = "green";

                    if (data.username) {
                        localStorage.setItem('username', data.username);
                        this.inputUsername = data.username;
                    }

                    this.newPassword = "";
                } else {
                    this.statusMessage = data.msg || "Update failed";
                    this.statusColor = "red";
                }
            } catch (error) {
                console.error("Error updating profile:", error);
                this.statusMessage = "Update failed";
                this.statusColor = "red";
            }
        },
        // friend logic
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
                    this.searchUserPfp = data.user.pfpUrl || '';
                    this.inputEmail = data.user.email || '';
                    this.searchUserBio = data.user.bio || '';
                    this.bioDraft = this.searchUserBio;

                    if (this.userId === id) {
                        this.friends = data.user.friends || [];
                        this.incomingRequests = data.user.incoming_requests || [];
                        this.outgoingRequests = data.user.outgoing_requests || [];
                    }
                }
            } catch (error) {
                console.error("Error loading profile:", error);
            }
        },
        toggleActionMenu(expense) {
            (this.activeGroup?.items || []).forEach(i => i.showActions = false);
            expense.showActions = !expense.showActions;
        },

        closeAllActionMenus() {
            (this.activeGroup?.items || []).forEach(i => i.showActions = false);
        },


        async prioritiseExpense(expense) {
            const newPriority = !expense.priority;

            const updates = newPriority
                ? { priority: true, priorityRank: Date.now() }
                : { priority: false, priorityRank: null };

            await this.updateExpense(expense.id, updates);
        },

        confirmRemoveExpense(expense) {
            this.closeAllActionMenus();
            this.selectedExpense = expense;
            this.showRemoveConfirm = true;
        },

        closeRemoveConfirm() {
            this.showRemoveConfirm = false;
            this.selectedExpense = null;
        },

        async removeSelectedExpense() {
            if (!this.selectedExpense) return;
            const id = this.selectedExpense.id;

            this.showRemoveConfirm = false;
            this.selectedExpense = null;

            await this.removeExpense(id);
        },

        openEditExpense(expense) {
            this.closeAllActionMenus();
            this.selectedExpense = expense;

            this.editExpenseData = {
                id: expense.id,
                name: expense.name || '',
                price: Number(expense.price || 0),
                quantity: Number(expense.quantity || 1),
                buyerUsername: (expense.buyer && expense.buyer.username) ? expense.buyer.username : (expense.buyer || ''),
                url: expense.url || ''
            };

            this.showEditExpenseModal = true;
        },

        closeEditExpense() {
            this.showEditExpenseModal = false;
            this.selectedExpense = null;
        },

        async saveEditExpense() {
            const e = this.editExpenseData;
            if (!e.id) return;

            if (!e.name || e.name.trim().length === 0) {
                alert("Description is required.");
                return;
            }

            const updates = {
                name: e.name.trim(),
                price: Number(e.price || 0),
                quantity: Number(e.quantity || 1),
                url: e.url ? e.url.trim() : null
            };

            if (e.buyerUsername && e.buyerUsername.trim()) {
                const allMembers = [...(this.activeGroup.admins || []), ...(this.activeGroup.users || [])];
                const buyerObj = allMembers.find(m => m.username === e.buyerUsername);
                updates.buyer = buyerObj ? { id: buyerObj.id, username: buyerObj.username } : { username: e.buyerUsername };
            } else {
                updates.buyer = null;
            }

            await this.updateExpense(e.id, updates);
            this.showEditExpenseModal = false;
        },


        async fetchMyData() {
            if (!this.userId) return;
            try {
                const response = await fetch('/get-user-details', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ userId: this.userId })
                });
                const data = await response.json();
                if (data.result && data.user) {
                    this.friends = data.user.friends || [];
                    this.incomingRequests = data.user.incoming_requests || [];
                    this.outgoingRequests = data.user.outgoing_requests || [];
                }
            } catch (e) { console.error("Error fetching my data:", e); }
        },

        async sendFriendRequest() {
            if (!this.userId) return;
            try {
                const response = await fetch('/friend/request', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        fromId: this.userId,
                        fromUsername: this.inputUsername,
                        toUsername: this.searchUsername
                    })
                });
                const data = await response.json();
                if (data.result) {
                    this.outgoingRequests.push(this.searchUsername);
                } else {
                    alert(data.msg);
                }
            } catch (e) { console.error(e); }
        },

        async respondRequest(friendUsername, accepted) {
            try {
                const response = await fetch('/friend/respond', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        userId: this.userId,
                        friendUsername: friendUsername,
                        accepted: accepted
                    })
                });
                const data = await response.json();
                if (data.result) {
                    this.incomingRequests = this.incomingRequests.filter(u => u !== friendUsername);
                    if (accepted) {
                        this.friends.push(friendUsername);
                    }
                    if (this.searchUsername === friendUsername) {
                        this.fetchUserProfile(this.searchUserId);
                    }
                }
            } catch (e) { console.error(e); }
        },

        async removeFriend() {
            if (!confirm(`Are you sure you want to remove ${this.searchUsername}?`)) return;
            try {
                const response = await fetch('/friend/remove', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        userId: this.userId,
                        friendUsername: this.searchUsername
                    })
                });
                const data = await response.json();
                if (data.result) {
                    this.friends = this.friends.filter(u => u !== this.searchUsername);
                    alert("Friend removed.");
                }
            } catch (e) { console.error(e); }
        },
        openCreateGroupModal() {
            this.showCreateGroupModal = true;
            this.newGroup = { name: '', description: '', budget: 0 };
            this.selectedAdmins = [{ id: this.userId, username: this.inputUsername }]; // Add self as admin
            this.selectedUsers = [];
            this.selectedGuests = [];
            this.memberSearchQuery = '';
            this.memberSearchResults = [];
        },

        async searchMembers() {
            if (this.memberSearchQuery.length < 2) {
                this.memberSearchResults = [];
                return;
            }
            this.searchLoading = true;
            try {
                const response = await fetch(`/user/search?q=${encodeURIComponent(this.memberSearchQuery)}`);
                const data = await response.json();

                // Filter out people already selected in ANY list
                const allSelectedIds = [
                    ...this.selectedAdmins,
                    ...this.selectedUsers,
                    ...this.selectedGuests
                ].map(u => u.id);

                this.memberSearchResults = (data.users || []).filter(u => !allSelectedIds.includes(u.id));
            } catch (e) {
                console.error(e);
            } finally {
                this.searchLoading = false;
            }
        },

        addMember(user, role) {
            if (role === 'admins') this.selectedAdmins.push(user);
            if (role === 'users') this.selectedUsers.push(user);
            if (role === 'guests') this.selectedGuests.push(user);

            this.memberSearchQuery = '';
            this.memberSearchResults = [];
        },

        removeMember(index, role) {
            if (role === 'admins') {
                if (this.selectedAdmins.length === 1) {
                    alert("Group must have at least one admin.");
                    return;
                }
                this.selectedAdmins.splice(index, 1);
            }
            if (role === 'users') this.selectedUsers.splice(index, 1);
            if (role === 'guests') this.selectedGuests.splice(index, 1);
        },

        async createGroup() {
            if (!this.newGroup.name) {
                alert("Please enter a group name.");
                return;
            }

            const payload = {
                name: this.newGroup.name,
                description: this.newGroup.description,
                budget: parseFloat(this.newGroup.budget),
                admins: this.selectedAdmins,
                users: this.selectedUsers,
                guests: this.selectedGuests,
                items: []
            };

            try {
                const response = await fetch('/group/create', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await response.json();

                if (data.result) {
                    this.showCreateGroupModal = false;
                    this.fetchMyGroups();
                    alert("Group created successfully!");
                } else {
                    alert("Error: " + data.msg);
                }
            } catch (e) {
                console.error(e);
                alert("Failed to create group.");
            }
        },
        openGroupSettings() {
            if (!this.activeGroup) return;
            this.editGroupData = {
                name: this.activeGroup.name,
                description: this.activeGroup.description || '',
                budget: this.activeGroup.budget
            };
            this.showGroupSettingsModal = true;
        },

        async saveGroupSettings() {
            try {
                const response = await fetch('/group/update-settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        groupId: this.activeGroup.groupId,
                        ...this.editGroupData
                    })
                });
                const data = await response.json();
                if (data.result) {
                    alert("Settings updated!");
                    this.showGroupSettingsModal = false;
                    this.fetchGroupDetails(this.activeGroup.groupId);
                } else {
                    alert("Update failed: " + data.msg);
                }
            } catch (e) { console.error(e); }
        },

        async changeMemberRole(member, newRole) {
            if (!confirm(`Change ${member.username}'s role to ${newRole}?`)) return;
            try {
                const response = await fetch('/group/member/role', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        groupId: this.activeGroup.groupId,
                        userId: member.id,
                        username: member.username,
                        role: newRole
                    })
                });
                const data = await response.json();
                if (data.result) {
                    this.fetchGroupDetails(this.activeGroup.groupId);
                } else {
                    alert(data.msg);
                }
            } catch (e) { console.error(e); }
        },

        async removeMember(member) {
            if (!confirm(`Remove ${member.username} from group?`)) return;
            try {
                const response = await fetch('/group/member/remove', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        groupId: this.activeGroup.groupId,
                        userId: member.id,
                        username: member.username
                    })
                });
                const data = await response.json();
                if (data.result) {
                    this.fetchGroupDetails(this.activeGroup.groupId);
                } else {
                    alert(data.msg);
                }
            } catch (e) { console.error(e); }
        },

        async leaveGroup() {
            if (!confirm("Are you sure you want to leave this group?")) return;
            try {
                const response = await fetch('/group/member/remove', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        groupId: this.activeGroup.groupId,
                        userId: this.userId,
                        username: this.inputUsername
                    })
                });
                const data = await response.json();
                if (data.result) {
                    window.location.href = '/display';
                } else {
                    alert(data.msg);
                }
            } catch (e) { console.error(e); }
        },

        async deleteGroup() {
            if (!confirm("WARNING: This will permanently delete the group and all expenses. Continue?")) return;
            try {
                const response = await fetch('/group/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ groupId: this.activeGroup.groupId })
                });
                const data = await response.json();
                if (data.result) {
                    alert("Group deleted.");
                    window.location.href = '/display';
                } else {
                    alert(data.msg);
                }
            } catch (e) { console.error(e); }
        },

        async togglePurchased(item) {
            const newStatus = !item.purchased;
            try {
                const response = await fetch('/update-item', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        groupId: this.activeGroup.groupId,
                        itemId: item.id,
                        updates: { purchased: newStatus }
                    })
                });
                const data = await response.json();
                if (data.result) {
                    item.purchased = newStatus;
                }
            } catch (e) { console.error(e); }
        },
        
        openAiModal() {
            this.showAiModal = true;
            this.aiData = { idea: '', people: 5, budget: 100, notes: '' };
        },

        async generateGroup() {
            if (!this.aiData.idea) {
                alert("Please give me a general idea!");
                return;
            }
            
            this.aiLoading = true;
            try {
                const response = await fetch('/group/ai-suggest', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.aiData)
                });
                const data = await response.json();
                
                if (data.result && data.items) {
                    this.showAiModal = false;
                    
                    this.openCreateGroupModal();
                    
                    this.newGroup.name = this.aiData.idea + " Group";
                    this.newGroup.description = this.aiData.idea;
                    this.newGroup.budget = this.aiData.budget;
                    this.newGroupItems = data.items;
                    
                } else {
                    alert("AI could not generate items: " + (data.msg || "Unknown error"));
                }
            } catch (e) {
                console.error(e);
                alert("Connection failed");
            } finally {
                this.aiLoading = false;
            }
        },

        openCreateGroupModal() {
            this.showCreateGroupModal = true;
            this.newGroup = { name: '', description: '', budget: 0 };
            this.selectedAdmins = [{ id: this.userId, username: this.inputUsername }];
            this.selectedUsers = [];
            this.selectedGuests = [];
            this.newGroupItems = [];
            this.memberSearchQuery = '';
            this.memberSearchResults = [];
        },

        async createGroup() {
            if (!this.newGroup.name) {
                alert("Please enter a group name.");
                return;
            }

            const payload = {
                name: this.newGroup.name,
                description: this.newGroup.description,
                budget: parseFloat(this.newGroup.budget),
                admins: this.selectedAdmins,
                users: this.selectedUsers,
                guests: this.selectedGuests,
                items: this.newGroupItems
            };

             try {
                const response = await fetch('/group/create', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await response.json();
                
                if (data.result) {
                    this.showCreateGroupModal = false;
                    this.fetchMyGroups(); 
                    alert("Group created successfully!");
                } else {
                    alert("Error: " + data.msg);
                }
            } catch (e) {
                console.error(e);
                alert("Failed to create group.");
            }
        },
        
        removeNewItem(index) {
            this.newGroupItems.splice(index, 1);
        }

    }
});