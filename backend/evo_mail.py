#!/usr/bin/env python3
"""
EvoMail - Self-Evolving Cognitive Agent for Spam Detection
Red-Team/Blue-Team framework for continuous adaptation
"""

import json
import random
import pickle
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
import hashlib
import os
from pathlib import Path

# ============================================
# CONFIGURATION
# ============================================

BASE_DIR = Path(__file__).resolve().parent
MEMORY_PATH = BASE_DIR / 'evo_memory.pkl'
MODEL_PATH = BASE_DIR / 'evo_model.pkl'
VECTORIZER_PATH = BASE_DIR / 'evo_vectorizer.pkl'

# ============================================
# MEMORY MODULE
# ============================================

class MemoryModule:
    """Compresses and stores experiences for future reasoning"""
    
    def __init__(self):
        self.experiences = []
        self.patterns = defaultdict(int)
        self.failures = []
        self.successes = []
        self.max_memory = 10000
        self.compression_threshold = 100
        
    def add_experience(self, experience):
        """Add new experience to memory"""
        self.experiences.append({
            'timestamp': datetime.now().isoformat(),
            'data': experience,
            'importance': experience.get('importance', 1)
        })
        
        # Compress if memory is full
        if len(self.experiences) > self.max_memory:
            self.compress()
            
        # Extract patterns
        if 'text' in experience:
            pattern = self.extract_pattern(experience['text'])
            self.patterns[pattern] += 1
            
    def extract_pattern(self, text):
        """Extract key pattern from text"""
        # Simple pattern extraction - can be enhanced with NLP
        words = text.lower().split()
        if len(words) > 3:
            return ' '.join(words[:3])  # Use first 3 words as pattern
        return text[:20]
    
    def compress(self):
        """Compress experiences to save memory"""
        # Keep only important experiences
        self.experiences.sort(key=lambda x: x['importance'], reverse=True)
        self.experiences = self.experiences[:self.max_memory // 2]
        
        # Keep only top patterns
        top_patterns = sorted(
            self.patterns.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:1000]
        self.patterns = defaultdict(int, dict(top_patterns))
        
    def get_relevant_experiences(self, text, limit=10):
        """Get experiences relevant to current text"""
        pattern = self.extract_pattern(text)
        relevant = []
        
        for exp in self.experiences:
            if pattern in exp['data'].get('text', ''):
                relevant.append(exp)
                
        return relevant[:limit]
    
    def get_failure_patterns(self, limit=20):
        """Get most common failure patterns"""
        failures = [e for e in self.experiences if e['data'].get('failed', False)]
        patterns = defaultdict(int)
        
        for f in failures:
            pattern = self.extract_pattern(f['data'].get('text', ''))
            patterns[pattern] += 1
            
        return sorted(patterns.items(), key=lambda x: x[1], reverse=True)[:limit]
    
    def save(self, path=MEMORY_PATH):
        """Save memory to disk"""
        with open(path, 'wb') as f:
            pickle.dump({
                'experiences': self.experiences,
                'patterns': dict(self.patterns),
                'failures': self.failures,
                'successes': self.successes
            }, f)
            
    def load(self, path=MEMORY_PATH):
        """Load memory from disk"""
        if os.path.exists(path):
            with open(path, 'rb') as f:
                data = pickle.load(f)
                self.experiences = data.get('experiences', [])
                self.patterns = defaultdict(int, data.get('patterns', {}))
                self.failures = data.get('failures', [])
                self.successes = data.get('successes', [])


# ============================================
# RED TEAM - Adversarial Generator
# ============================================

class RedTeam:
    """Generates novel evasion tactics to test the model"""
    
    def __init__(self):
        self.attack_types = [
            'character_substitution',
            'synonym_replacement',
            'noise_injection',
            'sentence_rephrasing',
            'homoglyph_attack',
            'padding_attack',
            'spacing_attack'
        ]
        
        self.substitutions = {
            'a': ['@', '4', 'á', 'â', 'à', 'α'],
            'e': ['3', 'é', 'è', 'ê', 'ë', 'ε'],
            'i': ['1', '!', 'í', 'ì', 'ι', '|'],
            'o': ['0', 'ó', 'ò', 'ö', 'ο'],
            's': ['$', '5', 'z', 'ş', 'σ'],
            't': ['7', '+', '†'],
            'l': ['1', '|', 'ł'],
            'b': ['8', '6', 'ß'],
            'g': ['9', '6', 'ğ'],
            'c': ['(', '<', '{', 'ç']
        }
        
        self.synonyms = {
            'free': ['complimentary', 'gratis', 'no cost', 'without charge', 'on the house', 'costless'],
            'claim': ['win', 'get', 'receive', 'earn', 'collect', 'obtain', 'acquire'],
            'prize': ['reward', 'bonus', 'award', 'gift', 'compensation', 'prize money'],
            'urgent': ['immediate', 'critical', 'important', 'pressing', 'essential', 'imperative'],
            'click': ['tap', 'press', 'visit', 'go to', 'access', 'navigate to'],
            'win': ['earn', 'gain', 'secure', 'achieve', 'attain', 'obtain'],
            'money': ['cash', 'funds', 'currency', 'capital', 'finances', 'wealth'],
            'limited': ['restricted', 'scant', 'minimal', 'finite', 'controlled', 'bounded']
        }
        
    def generate_attack(self, text, attack_type=None):
        """Generate an adversarial variant"""
        if not attack_type:
            attack_type = random.choice(self.attack_types)
            
        if attack_type == 'character_substitution':
            return self.character_substitution(text)
        elif attack_type == 'synonym_replacement':
            return self.synonym_replacement(text)
        elif attack_type == 'noise_injection':
            return self.noise_injection(text)
        elif attack_type == 'sentence_rephrasing':
            return self.sentence_rephrasing(text)
        elif attack_type == 'homoglyph_attack':
            return self.homoglyph_attack(text)
        elif attack_type == 'padding_attack':
            return self.padding_attack(text)
        elif attack_type == 'spacing_attack':
            return self.spacing_attack(text)
        return text
    
    def character_substitution(self, text, intensity=0.3):
        """Replace characters with visually similar alternatives"""
        result = []
        for char in text:
            if char.lower() in self.substitutions and random.random() < intensity:
                result.append(random.choice(self.substitutions[char.lower()]))
            else:
                result.append(char)
        return ''.join(result)
    
    def synonym_replacement(self, text, intensity=0.4):
        """Replace words with synonyms"""
        words = text.split()
        result = []
        for word in words:
            word_clean = word.lower().strip('.,!?')
            if word_clean in self.synonyms and random.random() < intensity:
                new_word = random.choice(self.synonyms[word_clean])
                # Preserve punctuation
                punct = ''
                if word and word[-1] in '.,!?':
                    punct = word[-1]
                    word = word[:-1]
                result.append(new_word + punct)
            else:
                result.append(word)
        return ' '.join(result)
    
    def noise_injection(self, text, intensity=0.15):
        """Insert random noise characters"""
        if len(text) < 5:
            return text
        result = list(text)
        noise_chars = [' ', '.', '!', '?', ',', ';', ':' , '-', '_', '*']
        
        num_noise = max(1, int(len(text) * intensity))
        positions = random.sample(range(len(text)), min(num_noise, len(text) - 1))
        for pos in sorted(positions, reverse=True):
            char = random.choice(noise_chars)
            result.insert(pos, char)
        return ''.join(result)
    
    def sentence_rephrasing(self, text):
        """Simple rule-based sentence rephrasing"""
        rules = [
            (r'claim your (.*?) now', r'you can get your \1 today'),
            (r'you have won', r'congratulations, you are the winner of'),
            (r'click here', r'visit this link'),
            (r'free (.*?)', r'complimentary \1'),
            (r'urgent', r'important'),
            (r'limited time', r'hurry, only for a short period'),
            (r'act now', r'don\'t delay, take action'),
        ]
        result = text
        for pattern, replacement in rules:
            import re
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        return result
    
    def homoglyph_attack(self, text):
        """Use visually similar characters from different scripts"""
        homoglyphs = {
            'a': 'а',  # Cyrillic
            'e': 'е',  # Cyrillic
            'o': 'о',  # Cyrillic
            'p': 'р',  # Cyrillic
            'c': 'с',  # Cyrillic
            'x': 'х',  # Cyrillic
            'y': 'у',  # Cyrillic
        }
        result = []
        for char in text:
            if char.lower() in homoglyphs and random.random() < 0.3:
                result.append(homoglyphs[char.lower()])
            else:
                result.append(char)
        return ''.join(result)
    
    def padding_attack(self, text):
        """Add padding characters between words"""
        words = text.split()
        padding = ['', '.', ',', '!', '?', ' ']
        padded = []
        for i, word in enumerate(words):
            padded.append(word)
            if i < len(words) - 1 and random.random() < 0.3:
                padded.append(random.choice(padding))
        return ' '.join(padded)
    
    def spacing_attack(self, text):
        """Insert extra spaces within words"""
        if len(text) < 5:
            return text
        result = []
        for char in text:
            result.append(char)
            if random.random() < 0.05:  # 5% chance of extra space
                result.append(' ')
        return ''.join(result)
    
    def generate_batch(self, texts, num_variants=3):
        """Generate multiple attacks for a batch of texts"""
        attacks = []
        for text in texts:
            for _ in range(num_variants):
                attack_type = random.choice(self.attack_types)
                variant = self.generate_attack(text, attack_type)
                attacks.append({
                    'original': text,
                    'variant': variant,
                    'attack_type': attack_type
                })
        return attacks


# ============================================
# BLUE TEAM - Adaptive Detector
# ============================================

class BlueTeam:
    """Learns from failures and adapts detection"""
    
    def __init__(self):
        self.model = None
        self.vectorizer = None
        self.label_encoder = None
        self.training_history = []
        self.failure_log = []
        self.adaptation_count = 0
        
    def load_model(self, model_path, vectorizer_path, label_encoder_path):
        """Load existing model"""
        import joblib
        self.model = joblib.load(model_path)
        self.vectorizer = joblib.load(vectorizer_path)
        self.label_encoder = joblib.load(label_encoder_path)
        
    def detect_failures(self, predictions, ground_truth):
        """Identify where the model failed"""
        failures = []
        for pred, truth in zip(predictions, ground_truth):
            if pred != truth:
                failures.append({
                    'predicted': pred,
                    'actual': truth,
                    'timestamp': datetime.now().isoformat()
                })
        return failures
    
    def learn_from_failure(self, failure_data, memory):
        """Learn from a failure"""
        self.failure_log.append(failure_data)
        
        # Add to memory
        memory.add_experience({
            'text': failure_data.get('text', ''),
            'predicted': failure_data.get('predicted', ''),
            'actual': failure_data.get('actual', ''),
            'failed': True,
            'importance': 2  # Higher importance
        })
        
        # Update adaptation count
        self.adaptation_count += 1
        
    def adapt(self, training_data, labels):
        """Adapt the model with new training data"""
        if not self.model or not self.vectorizer:
            return
            
        # Vectorize new data
        X_new = self.vectorizer.transform(training_data)
        y_new = self.label_encoder.transform(labels)
        
        # Incremental learning
        # For SVM, we need to retrain (simplified approach)
        # In production, use partial_fit if available
        
        # Log adaptation
        self.training_history.append({
            'timestamp': datetime.now().isoformat(),
            'num_samples': len(training_data),
            'adaptation': self.adaptation_count
        })
        
        return X_new, y_new


# ============================================
# COGNITIVE AGENT - Main Orchestrator
# ============================================

class CognitiveAgent:
    """Self-evolving cognitive agent for spam detection"""
    
    def __init__(self):
        self.memory = MemoryModule()
        self.red_team = RedTeam()
        self.blue_team = BlueTeam()
        self.evolution_cycle = 0
        self.config = {
            'evolution_interval_hours': 24,
            'min_samples_for_evolution': 10,
            'memory_size': 10000,
            'attack_variants': 3
        }
        
        # Load existing state if available
        self.load_state()
        
    def detect(self, text):
        """Detect spam with cognitive reasoning"""
        # Check memory for similar patterns
        relevant = self.memory.get_relevant_experiences(text, limit=5)
        
        # Get base prediction from model
        if self.blue_team.model:
            import joblib
            vector = self.blue_team.vectorizer.transform([text])
            prediction = self.blue_team.model.predict(vector)[0]
            confidence = self.get_confidence(text)
        else:
            prediction = 'ham'
            confidence = 0.5
            
        # Enhance with memory
        if relevant:
            memory_boost = self.memory_enhance(relevant, prediction)
            confidence = min(confidence + memory_boost, 0.99)
            
        return {
            'prediction': prediction,
            'confidence': confidence,
            'memory_used': len(relevant),
            'evolution_cycle': self.evolution_cycle
        }
    
    def get_confidence(self, text):
        """Get prediction confidence"""
        if not self.blue_team.model:
            return 0.5
        try:
            import joblib
            vector = self.blue_team.vectorizer.transform([text])
            if hasattr(self.blue_team.model, 'predict_proba'):
                proba = self.blue_team.model.predict_proba(vector)
                return float(max(proba[0]))
            elif hasattr(self.blue_team.model, 'decision_function'):
                decision = self.blue_team.model.decision_function(vector)
                proba = 1 / (1 + np.exp(-np.abs(decision)))
                return float(proba)
        except:
            pass
        return 0.5
    
    def memory_enhance(self, relevant, prediction):
        """Boost confidence based on memory"""
        # Count how many relevant experiences confirm the prediction
        confirmations = 0
        for exp in relevant:
            if exp['data'].get('predicted', '') == prediction:
                confirmations += 1
        boost = min(confirmations * 0.05, 0.2)  # Max 20% boost
        return boost
    
    def evolve(self, new_data=None):
        """Self-evolve the agent"""
        self.evolution_cycle += 1
        
        # Step 1: Generate attacks using Red Team
        if new_data:
            attacks = self.red_team.generate_batch(
                new_data, 
                num_variants=self.config['attack_variants']
            )
        else:
            # Use memory to generate attacks
            texts = []
            for exp in self.memory.experiences[-100:]:
                if 'text' in exp['data']:
                    texts.append(exp['data']['text'])
            if texts:
                attacks = self.red_team.generate_batch(
                    texts,
                    num_variants=self.config['attack_variants']
                )
            else:
                attacks = []
        
        # Step 2: Test Blue Team on attacks
        if attacks and self.blue_team.model:
            import joblib
            results = []
            for attack in attacks:
                variant = attack['variant']
                vector = self.blue_team.vectorizer.transform([variant])
                prediction = self.blue_team.model.predict(vector)[0]
                
                # Check if attack evaded detection
                # Assuming we want to detect spam
                if prediction == 'ham':  # Attack evaded detection
                    results.append({
                        'attack': attack,
                        'prediction': prediction,
                        'evaded': True
                    })
                    
            # Step 3: Learn from evaded attacks
            for result in results:
                if result['evaded']:
                    # Add to memory
                    self.memory.add_experience({
                        'text': result['attack']['variant'],
                        'original': result['attack']['original'],
                        'attack_type': result['attack']['attack_type'],
                        'predicted': 'ham',
                        'actual': 'spam',
                        'evaded': True,
                        'importance': 3  # High importance
                    })
                    
                    # Blue Team learns
                    self.blue_team.learn_from_failure({
                        'text': result['attack']['variant'],
                        'predicted': 'ham',
                        'actual': 'spam',
                        'attack_type': result['attack']['attack_type']
                    }, self.memory)
        
        # Step 4: Compress memory
        self.memory.compress()
        
        # Step 5: Save state
        self.save_state()
        
        return {
            'evolution_cycle': self.evolution_cycle,
            'attacks_generated': len(attacks),
            'evaded_attacks': len(results) if attacks else 0,
            'memory_size': len(self.memory.experiences),
            'timestamp': datetime.now().isoformat()
        }
    
    def save_state(self):
        """Save cognitive agent state"""
        self.memory.save(MEMORY_PATH)
        
    def load_state(self):
        """Load cognitive agent state"""
        if os.path.exists(MEMORY_PATH):
            self.memory.load(MEMORY_PATH)
            
    def get_stats(self):
        """Get agent statistics"""
        return {
            'evolution_cycle': self.evolution_cycle,
            'memory_size': len(self.memory.experiences),
            'patterns_count': len(self.memory.patterns),
            'failure_count': len(self.blue_team.failure_log),
            'adaptation_count': self.blue_team.adaptation_count,
            'attack_types': self.red_team.attack_types
        }


# ============================================
# EVOLUTION SCHEDULER
# ============================================

class EvolutionScheduler:
    """Schedules automatic evolution of the cognitive agent"""
    
    def __init__(self, agent):
        self.agent = agent
        self.last_evolution = None
        self.schedule = {
            'interval_hours': 24,
            'enabled': True
        }
        
    def check_and_evolve(self, force=False):
        """Check if evolution is needed"""
        if not self.schedule['enabled'] and not force:
            return None
            
        if force:
            return self.agent.evolve()
            
        now = datetime.now()
        if self.last_evolution:
            elapsed = (now - self.last_evolution).total_seconds() / 3600
            if elapsed >= self.schedule['interval_hours']:
                result = self.agent.evolve()
                self.last_evolution = now
                return result
        else:
            # First evolution
            result = self.agent.evolve()
            self.last_evolution = now
            return result
            
        return None
    
    def get_next_evolution_time(self):
        """Get next scheduled evolution time"""
        if not self.last_evolution:
            return datetime.now()
        return self.last_evolution + timedelta(hours=self.schedule['interval_hours'])


# ============================================
# MAIN - Standalone Execution
# ============================================

def main():
    print("=" * 60)
    print("🧠 EvoMail - Self-Evolving Cognitive Agent")
    print("=" * 60)
    
    # Create agent
    agent = CognitiveAgent()
    
    print(f"\n📊 Agent Stats:")
    stats = agent.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    print("\n🔄 Running initial evolution...")
    result = agent.evolve()
    print(f"   Evolution Cycle: {result['evolution_cycle']}")
    print(f"   Memory Size: {result['memory_size']}")
    
    # Create scheduler
    scheduler = EvolutionScheduler(agent)
    
    print("\n⏰ Scheduler Status:")
    print(f"   Enabled: {scheduler.schedule['enabled']}")
    print(f"   Interval: {scheduler.schedule['interval_hours']} hours")
    
    # Test detection
    test_texts = [
        "Claim your free prize now!",
        "Meeting at 10am tomorrow",
        "You have won a free iPhone!"
    ]
    
    print("\n🧪 Testing Detection:")
    for text in test_texts:
        result = agent.detect(text)
        print(f"   '{text[:30]}...' → {result['prediction']} (conf: {result['confidence']:.2f})")
    
    print("\n✅ EvoMail initialized successfully!")
    print(f"   Memory Path: {MEMORY_PATH}")
    
    return agent


if __name__ == "__main__":
    agent = main()