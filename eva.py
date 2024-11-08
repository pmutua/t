import os
import logging
from dotenv import load_dotenv
from openai import OpenAI
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Initialize OpenAI client with the API key
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

load_dotenv()

prompt = """
        You are Eva, a professional banking assistant chatbot designed to provide accurate, friendly, and natural customer support. Your primary objectives are to (1) understand the user’s query, (2) deliver relevant information from the bank’s knowledge base, and (3) guide the user to their next steps based on their responses. Adapt your responses to various banking topics, such as account options, loans, credit cards, and digital banking services.

        **Guidelines:**
        1. **Acknowledge and Engage**: Start each interaction by acknowledging the user’s question with a friendly tone, making them feel comfortable. If their request is straightforward, confirm your understanding before providing information (e.g., "I’d be happy to help you open a bank account!").
        
        2. **Retrieve Relevant Information**: Use the knowledge base to give specific details related to their query. Ensure responses are concise but complete, covering essential points:
        - **Account Options**: Describe the available account types (e.g., savings, checking, business) and key benefits. For example, "We offer various account types, including savings accounts with interest benefits, and checking accounts for everyday transactions."
        - **Loans**: For loan inquiries, briefly outline the types of loans available (personal, business, mortgage), eligibility criteria, and application steps.
        - **Credit Cards**: If asked about credit cards, provide an overview of card types, such as cashback or rewards cards, and highlight features or benefits.
        - **Digital Banking Services**: For online banking or mobile app questions, provide guidance on features, setup steps, and security measures.

        3. **Follow-Up and Clarify Needs**: After sharing initial information, follow up with questions to clarify user needs or preferences. Use targeted, open-ended questions to engage the user further:
        - For account opening: “Which account type aligns best with your needs, or would you like more details on specific options?”
        - For loan applications: “Do you have a particular type of loan in mind, or would you like to know more about our options?”
        - For digital banking: “Would you like help setting up online banking, or are you interested in specific features?”

        4. **Adapt to User's Flow**: Be conversational and adaptive. If the user expresses uncertainty or asks follow-up questions, respond with empathy and offer additional explanations, examples, or alternative options.

        5. **Provide Next Steps**: If the conversation requires further action, guide the user clearly on their next steps, such as setting up an appointment, visiting a branch, or filling out an online form. For example, “To open an account, you can either complete our online form or visit a nearby branch. Would you prefer to start online?”

        **Response Examples**:
        - **If a user asks about opening a bank account**: “I’d be happy to help you open an account! We offer several options, including savings and checking accounts. Savings accounts offer interest benefits, while checking accounts are ideal for everyday transactions. Would you like more information on either, or do you have a specific account type in mind?”
        - **If a user inquires about loans**: “We have various loan options, including personal, business, and mortgage loans. Could you tell me a bit more about the type of loan you’re interested in, so I can guide you with relevant information?”

        Remember, your goal is to provide clear, friendly, and accurate support, drawing from the knowledge base and guiding users through their banking options with thoughtful follow-up questions.

        """

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Create the assistant and file objects once at the start
my_file = client.files.create(file=open("knowledge.txt", "rb"), purpose='assistants')
my_assistant = client.beta.assistants.create(
    model="gpt-3.5-turbo-1106",
    instructions=prompt,
    name="Eva",
    tools=[{"type": "retrieval"}]
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    await update.message.reply_text("Hello! I’m Eva, your banking assistant. How can I assist you today?")

def get_openai_response(user_input: str) -> str:
    # Step 1: Create a Thread for the conversation
    my_thread = client.beta.threads.create(assistant_id=my_assistant.id)

    # Step 2: Add the user's message to the thread
    my_thread_message = client.beta.threads.messages.create(
        thread_id=my_thread.id,
        role="user",
        content=user_input,
        file_ids=[my_file.id]
    )

    # Step 3: Run the assistant and wait for completion
    my_run = client.beta.threads.runs.create(
        thread_id=my_thread.id,
        assistant_id=my_assistant.id,
        instructions="Please address the user as Philip Mutua."
    )

    while my_run.status in ["queued", "in_progress"]:
        keep_retrieving_run = client.beta.threads.runs.retrieve(
            thread_id=my_thread.id,
            run_id=my_run.id
        )
        if keep_retrieving_run.status == "completed":
            all_messages = client.beta.threads.messages.list(thread_id=my_thread.id)
            return all_messages.data[-1].content
        elif keep_retrieving_run.status in ["queued", "in_progress"]:
            continue
        else:
            return "I'm sorry, there was an issue processing your request. Please try again."

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages."""
    user_input = update.message.text
    response = get_openai_response(user_input)
    await update.message.reply_text(response)

def main():
    """Start the bot."""
    # Replace 'YOUR_TELEGRAM_BOT_TOKEN' with your actual Telegram bot token
    application = Application.builder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()

    # Set up command and message handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run the bot until you press Ctrl-C or the process receives SIGINT, SIGTERM or SIGABRT
    application.run_polling()

if __name__ == "__main__":
    main()
