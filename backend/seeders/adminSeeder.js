const User = require("../models/User");

const seedAdminUser = async () => {
  try {
    const adminExists = await User.findOne({ role: "admin" });
    if (!adminExists) {
      const email = process.env.ADMIN_EMAIL || "admin@example.com";
      const password = process.env.ADMIN_PASSWORD || "admin123";

      const adminExists = await User.findOne({
        $or: [
          { role: "admin" },
          { username: "admin" },
          { email: process.env.ADMIN_EMAIL },
        ],
      });

            console.log('Admin user created successfully');
            console.log(`Email: ${email}`);
            console.log(`Password: ${password}`);
        }
        console.error('Error seeding admin user:', error);
      if (!adminExists) {
        await User.create({
          username: "admin",
          name: "Admin",
          email,
          password,
          role: "admin",
        });

      console.log("Admin user created successfully");
      console.log(`Email: ${email}`);
      console.log(`Password: ${password}`);
    }
  } catch (error) {
    console.error("Error seeding admin user:", error);
  }
};

module.exports = seedAdminUser;
