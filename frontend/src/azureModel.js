const axios = require('axios');
require('dotenv').config();

const BASE_URL = process.env.AZURE_FUNCTION_URL;
const HOST_KEY = process.env.HOST_KEY;

function createUrl(path) {
    url = `${BASE_URL}${path}?code=${HOST_KEY}`
    console.log(url)
    return url;
}

const azureModel = {
    login: async (username, password) => {
        try {
            const response = await axios.post(createUrl("/user/login"), {
                username: username,
                password: password
            });
            console.log(response.data);
            return response.data;
        } catch (error) {
            console.error("Azure Login Error:", error.message);
            return { result: false, msg: "Connection to backend failed - check Azure" };
        }
    },

    register: async (username, password) => {
        try {
            const response = await axios.post(createUrl("/user/register"), {
                username: username,
                password: password
            });
            console.log(response.data);
            return response.data;
        } catch (error) {
            console.error("Azure Login Error:", error.message);
            return { result: false, msg: "Connection to backend failed - check Azure" };
        }
    },

    updateUser: async (userId, updates) => {
        try {
            const response = await axios.post(createUrl("/user/update"), {
                userId: userId,
                ...updates
            });
            return response.data;
        } catch (error) {
            console.error("Azure updateUser Error:", error.message);
            return { result: false, msg: "Failed to update user" };
        }
    },

    getGroupsByAdmin: async (username) => {
        try {
            return (await axios.get(createUrl("/group/list/admin"), { params: { username } })).data;
        } catch (e) { return { result: false, msg: "Error fetching admin groups" }; }
    },

    getGroupsByMember: async (username) => {
        try {
            return (await axios.get(createUrl("/group/list/member"), { params: { username } })).data;
        } catch (e) { return { result: false, msg: "Error fetching member groups" }; }
    },

    getGroupsByGuest: async (username) => {
        try {
            return (await axios.get(createUrl("/group/list/guest"), { params: { username } })).data;
        } catch (e) { return { result: false, msg: "Error fetching guest groups" }; }
    },

    getUserByName: async (username) => {
        try {
            const response = await axios.get(createUrl("/user/get/username"), {
                params: { username }
            });
            return response.data;
        } catch (error) {
            if (error.response && error.response.status === 404) {
                return { result: false, msg: "User not found" };
            }
            console.error("Azure getUserByName Error:", error.message);
            return { result: false, msg: "Connection failed" };
        }
    },

    getGroupById: async (groupId) => {
        try {
            const response = await axios.get(createUrl("/group/get"), {
                params: { groupId }
            });
            return response.data;
        } catch (error) {
            console.error("Azure getGroupById Error:", error.message);
            return { result: false, msg: "Group not found" };
        }
    },

    getUserById: async (userId) => {
        try {
            const response = await axios.get(createUrl("/user/get"), {
                params: { userId }
            });
            return response.data;
        } catch (error) {
            console.error("Azure getUserById Error:", error.message);
            return { result: false, msg: "User not found" };
        }
    },

    addItemToGroup: async (groupId, item) => {
        try {
            const response = await axios.post(createUrl("/group/item/add"), {
                groupId: groupId,
                item: item
            });
            return response.data;
        } catch (error) {
            console.error("Azure addItemToGroup Error:", error.message);
            return { result: false, msg: "Failed to add item" };
        }
    },

    removeItemFromGroup: async (groupId, itemId) => {
        try {
            const response = await axios.post(createUrl("/group/item/remove"), {
                groupId: groupId,
                itemId: itemId
            });
            return response.data;
        } catch (error) {
            console.error("Azure removeItemFromGroup Error:", error.message);
            return { result: false, msg: "Failed to remove item" };
        }
    },

    updateItem: async (groupId, itemId, updates) => {
        try {
            const response = await axios.post(createUrl("/group/item/update"), {
                groupId: groupId,
                itemId: itemId,
                updates: updates
            });
            return response.data;
        } catch (error) {
            console.error("Azure updateItem Error:", error.message);
            return { result: false, msg: "Failed to update item" };
        }
    },

    voteItem: async (groupId, itemId, username, action = "toggle") => {
        try {
            const response = await axios.post(createUrl("/group/item/vote"), {
                groupId: groupId,
                itemId: itemId,
                username: username,
                action: action
            });
            return response.data;
        } catch (error) {
            console.error("Azure voteItem Error:", error.message);
            return { result: false, msg: "Failed to vote on item" };
        }
    },

    sendFriendRequest: async (fromId, fromUsername, toUsername) => {
        try {
            const response = await axios.post(createUrl("/user/friend/request"), {
                id_from_username_request: fromId,
                from_username_request: fromUsername,
                to_username_request: toUsername
            });
            return response.data;
        } catch (error) {
            console.error("Azure sendFriendRequest Error:", error.message);
            return { result: false, msg: "Failed to send request" };
        }
    },

    respondFriendRequest: async (userId, friendUsername, accepted) => {
        try {
            const response = await axios.post(createUrl("/user/friend/response"), {
                userId: userId,
                friendUsername: friendUsername,
                accepted: accepted
            });
            return response.data;
        } catch (error) {
            console.error("Azure respondFriendRequest Error:", error.message);
            return { result: false, msg: "Failed to respond" };
        }
    },

    createGroup: async (groupData) => {
        try {
            const response = await axios.post(createUrl("/group/create"), groupData);
            return response.data;
        } catch (error) {
            console.error("Azure createGroup Error:", error.message);
            return { result: false, msg: "Failed to create group" };
        }
    },

    updateGroupSettings: async (groupId, name, description, budget) => {
        try {
            const requests = [
                axios.post(createUrl("/group/name/set"), { groupId, name }),
                axios.post(createUrl("/group/description/set"), { groupId, description }),
                axios.post(createUrl("/group/budget/set"), { groupId, budget: parseFloat(budget) })
            ];

            await Promise.all(requests);
            return { result: true };
        } catch (error) {
            console.error("Azure updateGroupSettings Error:", error.message);
            return { result: false, msg: "Failed to update settings" };
        }
    },

    changeMemberRole: async (groupId, userId, username, role) => {
        try {
            const response = await axios.post(createUrl("/group/user/role/change"), {
                groupId,
                user: { id: userId, username },
                role
            });
            return response.data;
        } catch (error) {
            console.error("Azure changeMemberRole Error:", error.message);
            return { result: false, msg: "Failed to change role" };
        }
    },

    removeMemberFromGroup: async (groupId, userId, username) => {
        try {
            const response = await axios.post(createUrl("/group/user/remove"), {
                groupId,
                user: { id: userId, username }
            });
            return response.data;
        } catch (error) {
            console.error("Azure removeMemberFromGroup Error:", error.message);
            return { result: false, msg: "Failed to remove member" };
        }
    },

    deleteGroup: async (groupId) => {
        try {
            const response = await axios.post(createUrl("/group/delete"), { groupId });
            return response.data;
        } catch (error) {
            console.error("Azure deleteGroup Error:", error.message);
            return { result: false, msg: "Failed to delete group" };
        }
    },

    getAiSuggestions: async (idea, people, budget, notes) => {
        try {
            const response = await axios.post(createUrl("/group/items/suggest"), {
                groupId: "generating_new_group",
                idea: idea,
                people: people,
                budget: budget,
                additional_notes: notes,
                addToGroup: false
            });
            return response.data;
        } catch (error) {
            console.error("Azure getAiSuggestions Error:", error.message);
            return { result: false, msg: "AI Generation failed" };
        }
    },

    deleteUser: async (userId) => {
        try {
            const response = await axios.post(`${BASE_URL}/user/delete`, { userId });
            return response.data;
        } catch (error) {
            console.error("Azure deleteUser Error:", error.message);
            return { result: false, msg: "Failed to delete user" };
        }
    },

    addMemberToGroup: async (groupId, user, role) => {
        try {
            const response = await axios.post(`${BASE_URL}/group/user/add`, {
                groupId, user, role
            });
            return response.data;
        } catch (error) {
            console.error("Azure addMemberToGroup Error:", error.message);
            return { result: false, msg: "Failed to add member" };
        }
    },
};

module.exports = azureModel;