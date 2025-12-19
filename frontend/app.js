'use strict';

const express = require('express');
const app = express();
const server = require('http').Server(app);
const fetch = (...args) =>
  import('node-fetch').then(({ default: fetch }) => fetch(...args));

const BACKEND_ENDPOINT = process.env.BACKEND || 'http://localhost:8181';
const AZURE_API_KEY = process.env.AZURE_API_KEY || null;

app.set('view engine', 'ejs');
app.use('/static', express.static('public'));


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