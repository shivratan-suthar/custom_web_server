from flask import Flask, request, Response
import requests

app = Flask(__name__)

@app.route('/proxy')
def proxy():
    url = request.args.get('url')
    if not url:
        return "URL missing", 400

    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }
        res = requests.get(url, headers=headers)
        html = res.text

        # Inject CSS + JS for reading features
        inject_css = """
        <style>
          body, * {
            font-size: 18px !important;
            line-height: 1.6 !important;
            color: #00ff00 !important;
            background-color: #000000 !important;
            max-width: 100% !important;
            word-wrap: break-word !important;
          }
        </style>
        """

        inject_js = """
        <script>
        const popup = document.createElement('div');
        Object.assign(popup.style, {
          position: 'absolute',
          background: '#000000cc',
          color: 'white',
          padding: '8px',
          borderRadius: '6px',
          zIndex: 999999,
          maxWidth: '300px',
          fontSize: '14px',
          display: 'none'
        });
        document.body.appendChild(popup);

        function showPopup(text, x, y) {
          popup.innerText = text;
          popup.style.left = x + 'px';
          popup.style.top = y + 'px';
          popup.style.display = 'block';
          setTimeout(() => popup.style.display = 'none', 5000);
        }

        document.addEventListener('dblclick', async e => {
          const word = window.getSelection().toString().trim();
          if (!word) return;
          const res = await fetch('https://api.mymemory.translated.net/get?q=' + word + '&langpair=en|hi');
          const data = await res.json();
          const translated = data.responseData.translatedText || 'No translation';
          showPopup('EN→HI: ' + translated, e.pageX, e.pageY);
        });

        let longPressTimer;
        document.addEventListener('mousedown', (e) => {
          longPressTimer = setTimeout(async () => {
            const word = window.getSelection().toString().trim();
            if (!word) return;
            const res = await fetch('https://api.dictionaryapi.dev/api/v2/entries/en/' + word);
            const data = await res.json();
            const meaning = data[0]?.meanings[0]?.definitions[0]?.definition || 'No definition';
            showPopup('Meaning: ' + meaning, e.pageX, e.pageY);
          }, 1000);
        });
        document.addEventListener('mouseup', () => clearTimeout(longPressTimer));
        <\/script>
        """

        # Inject after <head>
        if "<head" in html:
            html = html.replace("<head", "<head" + inject_css + inject_js)
        else:
            html = "<head>" + inject_css + inject_js + "</head>" + html

        return Response(html, content_type="text/html")

    except Exception as e:
        return f"Error loading URL: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
