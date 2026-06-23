const User = require('../models/User');

const seedAdminUser = async () => {
    try{
        const adminExists = await User.findOne({ role: 'admin' });
        if(!adminExists){
            const email = process.env.ADMIN_EMAIL || 'admin@example.com';
            const password = process.env.ADMIN_PASSWORD || 'admin123';

            await User.create({
                email,
                password,
                role: 'admin',
                name: 'Admin'
            });

            conso;e.log('Admin user created successfully');
            cnsole.log(`Email: ${email}`);
            console.log(`Password: ${password}`);
        }
    }catch(error){
        console.error('Error seeding admin user:', error);
    }
};

module.exports = seedAdminUser;