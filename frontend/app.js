'use strict';

const express = require('express');
const app = express();
const server = require('http').Server(app);
const azureModel = require('./src/azureModel');
const path = require('path');
const fs = require('fs');
const multer = require('multer');

app.set('view engine', 'ejs');
app.use('/static', express.static('public'));
app.use(express.json());

// profile picture upload
const pfpUploadDir = path.join(__dirname, 'public', 'uploads', 'pfp');
fs.mkdirSync(pfpUploadDir, { recursive: true });

const uploadPfp = multer({
  storage: multer.diskStorage({
    destination: (_req, _file, cb) => cb(null, pfpUploadDir),
    filename: (req, file, cb) => {
      const ext = path.extname(file.originalname).toLowerCase();
      const safeExt = ['.jpg', '.jpeg', '.png', '.webp'].includes(ext) ? ext : '.png';
      const userId = req.body?.userId || 'user';
      cb(null, `${userId}-${Date.now()}${safeExt}`);
    }
  }),
  limits: { fileSize: 2 * 1024 * 1024 },
  fileFilter: (_req, file, cb) => {
    const ok = ['image/jpeg', 'image/png', 'image/webp'].includes(file.mimetype);
    cb(ok ? null : new Error('Invalid file type'), ok);
  }
});

// View routes for dynamic pages
['/', 'display', 'group-view', 'profile', 'settings'].forEach((route, i) => {
  app.get(route === '/' ? route : `/${route}`, (req, res) => 
    res.render(i === 0 ? 'welcome' : route)
  );
});

// Helper for Azure model endpoints
const azureRoute = (path, method, logMsg) => {
  app.post(path, async (req, res) => {
    if (logMsg) console.log(logMsg, req.body);
    const result = await azureModel[method](...Object.values(req.body));
    if (path === '/get-user-details' && result.user?.password) delete result.user.password;
    res.json(result);
  });
};

// Azure model routes
azureRoute('/my-groups', 'getGroupsByAdmin', 'Fetching admin groups for user:');
azureRoute('/membership-groups', 'getGroupsByMember', 'Fetching membership groups for user:');
azureRoute('/get-group-details', 'getGroupById');
azureRoute('/get-group-by-id', 'getGroupById');
azureRoute('/get-user-details', 'getUserById');
azureRoute('/login', 'login', 'Login Request Received');
azureRoute('/register', 'register', 'Register Request Received');
azureRoute('/update-user', 'updateUser', 'Updating user');
azureRoute('/add-item', 'addItemToGroup', 'Add item request:');
azureRoute('/remove-item', 'removeItemFromGroup', 'Remove item request:');
azureRoute('/update-item', 'updateItem', 'Update item request:');
azureRoute('/vote-item', 'voteItem', 'Vote item request:');
azureRoute('/friend/request', 'sendFriendRequest');
azureRoute('/friend/respond', 'respondFriendRequest');
azureRoute('/friend/remove', 'removeFriend');
azureRoute('/user/delete', 'deleteUser');
azureRoute('/group/user/add', 'addMemberToGroup');
azureRoute('/group/create', 'createGroup', 'Create Group Request:');
azureRoute('/group/update-settings', 'updateGroupSettings');
azureRoute('/group/member/role', 'changeMemberRole');
azureRoute('/group/member/remove', 'removeMemberFromGroup');
azureRoute('/group/delete', 'deleteGroup');
azureRoute('/group/items/suggest', 'getAiSuggestions');

app.post('/newExpense', async (req, res) => {
  console.log('New Expense Request');
  res.json(result);
});

app.post('/upload-pfp', uploadPfp.single('pfp'), async (req, res) => {
  try {
    if (!req.file) return res.status(400).json({ result: false, msg: 'No file uploaded' });
    return res.json({ result: true, pfpUrl: `/static/uploads/pfp/${req.file.filename}` });
  } catch (e) {
    return res.status(500).json({ result: false, msg: e.message || 'Upload failed' });
  }
});

app.get('/user/search', async (req, res) => {
  const result = await azureModel.searchUsers(req.query.q);
  res.json(result);
});

function startServer() {
  const PORT = process.env.PORT || 8080;
  server.listen(PORT, () => console.log(`Server listening on port ${PORT}`));
}

if (module === require.main) startServer();

module.exports = server;