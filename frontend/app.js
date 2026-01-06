'use strict';

const express = require('express');
const app = express();
const server = require('http').Server(app);
const azureModel = require('./src/azureModel');
const fetch = (...args) =>
  import('node-fetch').then(({ default: fetch }) => fetch(...args));

const path = require('path');
const fs = require('fs');
const multer = require('multer');


app.set('view engine', 'ejs');
app.use('/static', express.static('public'));
const pfpUploadDir = path.join(__dirname, 'public', 'uploads', 'pfp');
fs.mkdirSync(pfpUploadDir, { recursive: true });

const pfpStorage = multer.diskStorage({
  destination: (_req, _file, cb) => cb(null, pfpUploadDir),
  filename: (req, file, cb) => {
    const ext = path.extname(file.originalname).toLowerCase();
    const allowed = ['.jpg', '.jpeg', '.png', '.webp'];
    const safeExt = allowed.includes(ext) ? ext : '.png';
    const userId = (req.body && req.body.userId) ? String(req.body.userId) : 'user';
    cb(null, `${userId}-${Date.now()}${safeExt}`);
  }
});

const uploadPfp = multer({
  storage: pfpStorage,
  limits: { fileSize: 2 * 1024 * 1024 },
  fileFilter: (_req, file, cb) => {
    const ok = ['image/jpeg', 'image/png', 'image/webp'].includes(file.mimetype);
    cb(ok ? null : new Error('Invalid file type'), ok);
  }
});

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

app.post('/update-user', async (req, res) => {
  console.log(`Updating user ${req.body.userId}`);
    const { userId, updates } = req.body;
    const result = await azureModel.updateUser(userId, updates);
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

app.post('/get-group-by-id', async (req, res) => {
    const { groupId } = req.body;
    const result = await azureModel.getGroupById(groupId);
    res.json(result);
});

app.post('/get-user-details', async (req, res) => {
    const { userId } = req.body;
    const result = await azureModel.getUserById(userId);
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

app.post('/add-item', async (req, res) => {
    console.log('Add item request:', req.body);
    const { groupId, item } = req.body;
    const result = await azureModel.addItemToGroup(groupId, item);
    res.json(result);
});

app.post('/remove-item', async (req, res) => {
    console.log('Remove item request:', req.body);
    const { groupId, itemId } = req.body;
    const result = await azureModel.removeItemFromGroup(groupId, itemId);
    res.json(result);
});

app.post('/update-item', async (req, res) => {
    console.log('Update item request:', req.body);
    const { groupId, itemId, updates } = req.body;
    const result = await azureModel.updateItem(groupId, itemId, updates);
    res.json(result);
});

app.post('/vote-item', async (req, res) => {
    console.log('Vote item request:', req.body);
    const { groupId, itemId, username, action } = req.body;
    const result = await azureModel.voteItem(groupId, itemId, username, action);
    res.json(result);
});

app.post('/friend/request', async (req, res) => {
  const { fromId, fromUsername, toUsername } = req.body;
  const result = await azureModel.sendFriendRequest(fromId, fromUsername, toUsername);
  res.json(result);
});

app.post('/friend/respond', async (req, res) => {
  const { userId, friendUsername, accepted } = req.body;
  const result = await azureModel.respondFriendRequest(userId, friendUsername, accepted);
  res.json(result);
});

app.post('/friend/remove', async (req, res) => {
  const { userId, friendUsername } = req.body;
  const result = await azureModel.removeFriend(userId, friendUsername);
  res.json(result);
});

app.post('/user/delete', async (req, res) => {
  const { userId } = req.body;
  const result = await azureModel.deleteUser(userId);
  res.json(result);
});

app.post('/group/member/add', async (req, res) => {
  const { groupId, user, role } = req.body;
  const result = await azureModel.addMemberToGroup(groupId, user, role);
  res.json(result);
});

app.post('/group/user/add', async (req, res) => {
  const { groupId, user, role } = req.body;
  const result = await azureModel.addMemberToGroup(groupId, user, role);
  res.json(result);
});

app.post('/upload-pfp', uploadPfp.single('pfp'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ result: false, msg: 'No file uploaded' });
    }

    const pfpUrl = `/static/uploads/pfp/${req.file.filename}`;

    return res.json({ result: true, pfpUrl });
  } catch (e) {
    return res.status(500).json({ result: false, msg: e.message || 'Upload failed' });
  }
});

app.get('/user/search', async (req, res) => {
  const { q } = req.query;
  const result = await azureModel.searchUsers(q);
  res.json(result);
});

app.post('/group/create', async (req, res) => {
  console.log("Create Group Request:", req.body);
  const result = await azureModel.createGroup(req.body);
  res.json(result);
});

app.post('/group/update-settings', async (req, res) => {
  const { groupId, name, description, budget } = req.body;
  const result = await azureModel.updateGroupSettings(groupId, name, description, budget);
  res.json(result);
});

app.post('/group/member/role', async (req, res) => {
  const { groupId, userId, username, role } = req.body;
  const result = await azureModel.changeMemberRole(groupId, userId, username, role);
  res.json(result);
});

app.post('/group/member/remove', async (req, res) => {
  const { groupId, userId, username } = req.body;
  const result = await azureModel.removeMemberFromGroup(groupId, userId, username);
  res.json(result);
});

app.post('/group/delete', async (req, res) => {
  const { groupId } = req.body;
  const result = await azureModel.deleteGroup(groupId);
  res.json(result);
});

app.post('/group/items/suggest', async (req, res) => {
  const { idea, people, budget, notes } = req.body;
  const result = await azureModel.getAiSuggestions(idea, people, budget, notes);
  res.json(result);
});

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