const Groq = require("groq-sdk");

function createGroqClient() {
  const apiKey = process.env.GROQ_API_KEY;
  
  if (!apiKey || apiKey === 'your_groq_api_key_here') {
    console.warn('[xaiController] GROQ_API_KEY is not set or is placeholder');
    return null;
  }

  try {
    return new Groq({
      apiKey: apiKey
    });
  } catch (error) {
    console.error('[xaiController] Failed to create Groq client:', error);
    return null;
  }
}

const explainPrediction = async (req, res) => {
  const { text, prediction } = req.body;

  if (!text || !prediction) {
    return res.status(400).json({ error: "Text and prediction are required." });
  }

  const prompt = `You are a security assistant. A message was classified as "${prediction}" by our spam filter. 
Message: "${text}"

Provide a brief, 2-sentence explanation of what red flags or patterns exist in this message that make it suspicious or safe. Be concise and write in a user-friendly tone.`;

  const groq = createGroqClient();
  if (!groq) {
    return res.status(500).json({ error: "Groq client is not configured. Please check your GROQ_API_KEY." });
  }

  // Model hierarchy with fallback
  const models = [
    process.env.GROQ_MODEL || "llama-3.1-8b-instant",
    "llama3-8b-8192",
    "gemma2-9b-it"
  ];

  let lastError = null;

  for (const model of models) {
    try {
      console.log(`[xaiController] Requesting prediction explanation using model: ${model}`);
      const chatCompletion = await groq.chat.completions.create({
        messages: [{ role: 'user', content: prompt }],
        model: model,
        temperature: 0.5,
        max_tokens: 150,
      });

      const explanation = chatCompletion.choices[0]?.message?.content;
      if (explanation) {
        return res.json({ explanation });
      }
    } catch (error) {
      console.warn(`[xaiController] Model ${model} failed:`, error.message);
      lastError = error;
    }
  }

  console.error('[xaiController] All models failed to generate explanation:', lastError);
  res.status(500).json({ error: "Failed to generate explanation using AI." });
};

module.exports = { explainPrediction };
