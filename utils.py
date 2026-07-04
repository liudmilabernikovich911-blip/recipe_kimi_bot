def detect_language(text: str) -> str:
    if any("\u0400" <= char <= "\u04FF" for char in text):
        return "ru"
    return "en"

def get_texts(lang: str):
    return {
        "ru": {
            "welcome": (
                "👋 Привет! Я бот для генерации рецептов!\n\n"
                "🍳 Отправь мне список продуктов через запятую, "
                "и я пришлю готовые рецепты.\n\n"
                "Пример: «Курица, картошка, лук, морковь, сметана»"
            ),
            "help": (
                "📖 Как пользоваться:\n\n"
                "1. Напиши список продуктов\n"
                "2. Бот отправит запрос в Kimi AI\n"
                "3. Получишь рецепты с пошаговыми инструкциями\n\n"
                "💡 Чем больше продуктов — тем больше вариантов.\n\n"
                "Команды:\n/start — Начать\n/help — Помощь"
            ),
            "processing": (
                "🍳 Анализирую продукты и ищу лучшие рецепты…\n"
                "⏳ Это займёт несколько секунд."
            ),
            "recipes_header": "🍽️ Вот рецепты для твоих продуктов:",
            "error": (
                "❌ Произошла ошибка при получении рецептов.\n"
                "Попробуйте позже или проверьте список продуктов."
            ),
            "restart_btn": "🔄 Новый запрос",
            "restart_prompt": "Отправь новый список продуктов, и я подберу рецепты!",
            "system_prompt": (
                "Ты — опытный шеф-повар. Предложи рецепты готовых блюд "
                "на основе имеющихся продуктов. Для каждого рецепта укажи:\n"
                "- Название блюда\n"
                "- Время приготовления\n"
                "- Сложность (лёгкая/средняя/сложная)\n"
                "- Пошаговые инструкции\n"
                "- Количество порций\n\n"
                "Если продуктов не хватает — предложи, что докупить. "
                "Отвечай на русском языке."
            ),
            "user_prompt": "У меня есть: {ingredients}. Предложи рецепты.",
        },
        "en": {
            "welcome": (
                "👋 Hi! I'm a recipe generation bot!\n\n"
                "🍳 Send me a list of ingredients you have, "
                "and I'll send you ready-made recipes.\n\n"
                'Example: "Chicken, potatoes, onion, carrots, sour cream"'
            ),
            "help": (
                "📖 How to use:\n\n"
                "1. Write a list of ingredients\n"
                "2. The bot sends a request to Kimi AI\n"
                "3. You get recipes with step-by-step instructions\n\n"
                "💡 The more ingredients, the more options.\n\n"
                "Commands:\n/start — Start\n/help — Help"
            ),
            "processing": (
                "🍳 Analyzing ingredients and looking for the best recipes…\n"
                "⏳ This will take a few seconds."
            ),
            "recipes_header": "🍽️ Here are recipes for your ingredients:",
            "error": (
                "❌ An error occurred while getting recipes.\n"
                "Please try again later or check your ingredient list."
            ),
            "restart_btn": "🔄 New Request",
            "restart_prompt": "Send a new list of ingredients and I'll find recipes!",
            "system_prompt": (
                "You are an experienced chef. Suggest ready-made dishes "
                "based on available ingredients. For each recipe include:\n"
                "- Dish name\n"
                "- Cooking time\n"
                "- Difficulty (easy/medium/hard)\n"
                "- Step-by-step instructions\n"
                "- Number of servings\n\n"
                "If ingredients are insufficient, suggest what to buy. "
                "Answer in English."
            ),
            "user_prompt": "I have: {ingredients}. Suggest recipes.",
        },
    }[lang]