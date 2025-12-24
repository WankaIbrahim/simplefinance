const azureModel = {
    login: async (username, password) => {
        // Placeholder for Azure login logic
        // Update 24/12: make it so anyone can login just to test functionality
        // if(username === 'test' && password === 'test') {
            return { success: true, message: 'Login successful' };
        // }else{
        //     return { success: false, message: 'Invalid credentials: test test' };
        // }
    },
    register: async (username, password) => {
        // Placeholder for Azure login logic
       
            return { success: true, message: 'Register successful' };
    }
}

module.exports = azureModel;