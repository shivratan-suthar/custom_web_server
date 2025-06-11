from flask import Flask, request, Response
import requests
import re

app = Flask(__name__)

@app.route('/proxy')
def proxy():
    url = request.args.get('url')
    text_color = request.args.get('text', '00ff00')  # Default: green
    bg_color = request.args.get('bg', '000000')      # Default: black

    if not url:
        return "URL missing", 400

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        html = res.text

        # Inject CSS
        inject_css = f"""
        <style>
          body, * {{
            font-size: 18px !important;
            line-height: 1.6 !important;
            color: #{text_color} !important;
            background-color: #{bg_color} !important;
            max-width: 100% !important;
            word-wrap: break-word !important;
          }}
        </style>
        """

        # Inject JS
        inject_js = """
        <script>
        const popup = document.createElement('div');
        Object.assign(popup.style, {
          position: 'absolute',
          background: '#000000e0',
          color: 'white',
          padding: '10px',
          borderRadius: '8px',
          zIndex: 999999,
          maxWidth: '320px',
          fontSize: '15px',
          fontFamily: 'sans-serif',
          display: 'none'
        });
        document.body.appendChild(popup);

        function showPopup(htmlContent, x, y) {
          popup.innerHTML = htmlContent;
          popup.style.left = x + 'px';
          popup.style.top = y + 'px';
          popup.style.display = 'block';
          setTimeout(() => popup.style.display = 'none', 8000);
        }

        // 🔍 Translation on Double Click
        document.addEventListener('dblclick', async e => {
          const word = window.getSelection().toString().trim();
          if (!word) return;
          const res = await fetch('https://api.mymemory.translated.net/get?q=' + encodeURIComponent(word) + '&langpair=en|hi');
          const data = await res.json();
          const translated = data.responseData.translatedText || 'No translation found';
          showPopup('<b>Translation (EN → HI):</b><br>' + translated, e.pageX, e.pageY);
        });

        // 📖 Dictionary on Long Press
        let longPressTimer;
        document.addEventListener('mousedown', (e) => {
          longPressTimer = setTimeout(async () => {
            const word = window.getSelection().toString().trim();
            if (!word) return;

            try {
              const res = await fetch('https://api.dictionaryapi.dev/api/v2/entries/en/' + encodeURIComponent(word));
              const data = await res.json();
              const entry = data[0];
              const meaning = entry.meanings[0];
              const def = meaning.definitions[0];

              const definition = def.definition || "No definition found.";
              const partOfSpeech = meaning.partOfSpeech || "unknown";
              const example = def.example ? "<br><i>Example:</i> " + def.example : "";

              showPopup('<b>' + word + '</b> <i>(' + partOfSpeech + ')</i><br>' + definition + example, e.pageX, e.pageY);
            } catch {
              showPopup('⚠️ No dictionary data found.', e.pageX, e.pageY);
            }
          }, 1000);
        });

        document.addEventListener('mouseup', () => clearTimeout(longPressTimer));
        </script>
        """

        # Inject after <head>
        html = re.sub(r"<head.*?>", lambda m: m.group(0) + inject_css + inject_js, html, count=1)

        return Response(html, content_type="text/html")

    except Exception as e:
        return f"Error loading URL: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)
