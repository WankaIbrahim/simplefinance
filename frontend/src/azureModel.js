const axios = require('axios');
require('dotenv').config();

const BASE_URL = process.env.AZURE_FUNCTION_URL;

const azureModel = {
    login: async (username, password) => {
        try {
            const response = await axios.post(`${BASE_URL}/user/login`, {
                username: username,
                password: password
            });
            console.log(response.data);
            return response.data;
        } catch (error) {
            // console.log("Azure Login Error: " + error.message);
            console.error("Azure Login Error:", error.message);
            return { result: false, msg: "Connection to backend failed - check Azure" };
        }
    },
    register: async (username, password) => {
        try {
            const response = await axios.post(`${BASE_URL}/user/register`, {
                username: username,
                password: password
            });
            console.log(response.data);
            return response.data;
        } catch (error) {
            // console.log("Azure Login Error: " + error.message);
            console.error("Azure Login Error:", error.message);
            return { result: false, msg: "Connection to backend failed - check Azure" };
        }
    },

    getGroupsByAdmin: async (username) => {
        try {
            return (await axios.get(`${BASE_URL}/group/list/admin`, { params: { username } })).data;
        } catch (e) { return { result: false, msg: "Error fetching admin groups" }; }
    },

    getGroupsByMember: async (username) => {
        try {
            return (await axios.get(`${BASE_URL}/group/list/member`, { params: { username } })).data;
        } catch (e) { return { result: false, msg: "Error fetching member groups" }; }
    },

    getGroupsByGuest: async (username) => {
        try {
            return (await axios.get(`${BASE_URL}/group/list/guest`, { params: { username } })).data;
        } catch (e) { return { result: false, msg: "Error fetching guest groups" }; }
    },
    getUserByName: async (username) => {
        try {
            const response = await axios.get(`${BASE_URL}/user/get/username`, {
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
            const response = await axios.get(`${BASE_URL}/group/get`, {
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
            const response = await axios.get(`${BASE_URL}/user/get`, {
                params: { userId }
            });
            return response.data;
        } catch (error) {
            console.error("Azure getUserById Error:", error.message);
            return { result: false, msg: "User not found" };
        }
    },
}

module.exports = azureModel;