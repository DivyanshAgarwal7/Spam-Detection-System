const express = require("express");
const router = express.Router();
const Groq = require("groq-sdk");

const groq = new Groq({
    apiKey: process.env.GROQ_API_KEY || "placeholder_key"
});

const { chatLimiter } = require("../middleware/rateLimiter");

// The system prompt defines the assistant's persona and limits.
const SYSTEM_PROMPT = `You are the Spam Detection System Security Assistant. Your purpose is purely educational.

Guidelines:
1. Explain how to use this application and describe its features and functionalities.
2. Provide prevention tips and best security practices.
3. Explain concepts like email scams, SMS scams, phishing, and malicious URLs.
4. If a query is unrelated to cybersecurity awareness, spam detection, phishing, malicious URLs, email security, SMS scams, or application usage, politely explain that the assistant is limited to security education topics.
5. Never claim certainty about whether a URL, email, SMS, or message is safe. Instead, explain indicators and recommend verification steps.`;

router.post("/", chatLimiter, async (req, res) => {
    try {
        const { message, history } = req.body;

        if (!message) {
            return res.status(400).json({ error: "Message is required." });
        }

        if (message.length > 1000) {
            return res.status(400).json({ error: "Message exceeds maximum length of 1000 characters." });
        }

        // Format the history for Groq
        const messages = [
            { role: "system", content: SYSTEM_PROMPT }
        ];

        if (history && Array.isArray(history)) {
            // Append history up to a certain limit to avoid hitting token limits
            const recentHistory = history.slice(-10);
            for (const msg of recentHistory) {
                if (msg.role && msg.content) {
                    messages.push({ role: msg.role, content: msg.content });
                }
            }
        }

        messages.push({ role: "user", content: message });

        const chatCompletion = await groq.chat.completions.create({
            messages: messages,
            model: "llama-3.1-8b-instant",
            temperature: 0.5,
            max_tokens: 1024,
            top_p: 1,
            stop: null,
            stream: false,
        });

        const reply = chatCompletion.choices[0]?.message?.content || "I am currently unable to process your request.";
        
        res.json({ reply });
    } catch (error) {
        console.error("Groq API error:", error);
        res.status(500).json({ error: "Failed to communicate with Security Assistant." });
    }
});

module.exports = router;
