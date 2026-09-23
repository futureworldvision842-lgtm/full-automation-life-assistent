import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from src.openhuman_cognitive_engine import MemoryTreeManager
from src.ai_learning_engine import AILearningEngine

memory = MemoryTreeManager()
ai_engine = AILearningEngine()

lesson = "STRICT_TREND_DOMINANCE: Never short Gold during strong H1 Bullish trend days; minor M15 sweep wicks are continuation traps, not reversals. Gold must ONLY trade with the H1 trend."
memory.store_lesson("GOLD_PATTERNS", lesson, importance_score=5)
ai_engine.update_pattern_outcome("BEARISH_SWEEP", is_win=False)

print("SUCCESS: Lesson stored into OpenHuman MemoryTree and BEARISH_SWEEP penalized.")
