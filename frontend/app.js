'use strict';

const express = require('express');
const app = express();
const server = require('http').Server(app);
const azureModel = require('./src/azureModel');
const fetch = (...args) =>
  import('node-fetch').then(({ default: fetch }) => fetch(...args));

const BACKEND_ENDPOINT = process.env.BACKEND || 'http://localhost:8181';
const AZURE_API_KEY = process.env.AZURE_API_KEY || null;

app.set('view engine', 'ejs');
app.use('/static', express.static('public'));
app.use(express.json());

app.get('/', (req, res) => {
    res.render('welcome');
});

app.get('/display', (req, res) => {
    res.render('display');
});
app.get('/group-view', (req, res) => {
    res.render('group-view');
});
app.get('/profile', (req, res) => {
    res.render('profile');
});
app.get("/settings", (req, res) => {
  res.render("settings");
});


app.post('/my-groups', async (req, res) => {
    console.log('Fetching admin groups for user:', req.body.username);
    const { username } = req.body;
    const result = await azureModel.getGroupsByAdmin(username);
    res.json(result);
});

app.post('/membership-groups', async (req, res) => {
    console.log('Fetching membership groups for user:', req.body.username);
    const { username } = req.body;
    const result = await azureModel.getGroupsByMember(username);
    res.json(result);
});
app.post('/get-group-details', async (req, res) => {
    const { groupId } = req.body;
    const result = await azureModel.getGroupById(groupId);
    res.json(result);
});
//
app.post('/get-group-by-id', async (req, res) => {
    const { groupId } = req.body;
    const result = await azureModel.getGroupById(groupId);
    res.json(result);
});

app.post('/get-user-details', async (req, res) => {
    const { userId } = req.body;
    const result = await azureModel.getUserById(userId);
    // Security Note: You might want to remove password before sending to frontend
    if (result.user && result.user.password) {
        delete result.user.password;
    }
    res.json(result);
});

app.post('/login', async (req, res) => {
    console.log('Login Request Received');
    const { username, password } = req.body;
    const result = await azureModel.login(username, password);
    res.json(result);
});
app.post('/register', async (req, res) => {
    console.log('Register Request Received');
    const { username, password } = req.body;
    const result = await azureModel.register(username, password);
    res.json(result);
});

app.post('/newExpense', async (req, res) => {
    console.log('New Expense Request');
    const { item, amount, payer } = req.body;
    // const result = await azureModel.newExpense(item, amount, payer);
    res.json(result);
});


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