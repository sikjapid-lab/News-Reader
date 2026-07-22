import gradio as gr
from transformers import pipeline

# Load English to Persian Translation Model
translator = pipeline("translation_en_to_fa", model="Helsinki-NLP/opus-mt-en-fa")

def process_and_translate(text):
    if not text:
        return "متنی ارسال نشده است."
    try:
        translated = translator(text, max_length=512)
        return translated[0]['translation_text']
    except Exception as e:
        return f"خطا در پردازش: {str(e)}"

# Gradio Interface for Hugging Face Space
demo = gr.Interface(
    fn=process_and_translate,
    inputs=gr.Textbox(lines=4, placeholder="متن انگلیسی خبر را وارد کنید..."),
    outputs=gr.Textbox(lines=4, label="ترجمه روان فارسی"),
    title="موتور هوش مصنوعی ترجمه اخبار جهان‌نما",
    description="سرویس ابری پردازش و ترجمه اخبار بین‌الملل جهت پشتیبانی از وب‌سایت گیت‌هاب"
)

if __name__ == "__main__":
    demo.launch()
