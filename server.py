from flask import Flask, request, Response
import requests
import re

app = Flask(__name__)

@app.route('/proxy')
def proxy():
    url = request.args.get('url')
    text_color = request.args.get('text', '00ff00')
    bg_color = request.args.get('bg', '000000')

    if not url:
        return "URL missing", 400

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        html = res.text

        # Fallback if no <head>
        if '<head' not in html:
            html = "<html><head></head><body>" + html + "</body></html>"

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

        inject_js = """
        <script>
        window.addEventListener('DOMContentLoaded', () => {
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

          function showPopup(html, x, y) {
            popup.innerHTML = html;
            popup.style.left = x + 'px';
            popup.style.top = y + 'px';
            popup.style.display = 'block';
            setTimeout(() => popup.style.display = 'none', 8000);
          }

          let longPressTimer;
          document.addEventListener('mousedown', (e) => {
            longPressTimer = setTimeout(async () => {
              const word = window.getSelection().toString().trim();
              if (!word) return;
              try {
                const res = await fetch('https://api.dictionaryapi.dev/api/v2/entries/en/' + encodeURIComponent(word));
                const data = await res.json();
                const entry = data[0];
                const def = entry.meanings[0].definitions[0];
                const html = '<b>' + word + '</b> <i>(' + entry.meanings[0].partOfSpeech + ')</i><br>' +
                             def.definition + (def.example ? '<br><i>Example:</i> ' + def.example : '');
                showPopup(html, e.pageX, e.pageY);
              } catch {
                showPopup('⚠️ No dictionary result', e.pageX, e.pageY);
              }
            }, 1000);
          });
          document.addEventListener('mouseup', () => clearTimeout(longPressTimer));

          document.addEventListener('dblclick', async e => {
            const word = window.getSelection().toString().trim();
            if (!word) return;
            const res = await fetch('https://api.mymemory.translated.net/get?q=' + encodeURIComponent(word) + '&langpair=en|hi');
            const data = await res.json();
            const translated = data.responseData.translatedText || 'No translation found';
            showPopup('<b>Translation:</b><br>' + translated, e.pageX, e.pageY);
          });

          document.addEventListener('mouseup', async e => {
            const selection = window.getSelection().toString().trim();
            if (selection.length > 1) {
              const res = await fetch('https://api.mymemory.translated.net/get?q=' + encodeURIComponent(selection) + '&langpair=en|hi');
              const data = await res.json();
              const translated = data.responseData.translatedText;
              const html = '<b>EN → HI:</b><br>' + translated + '<br><button onclick="navigator.clipboard.writeText(\\'' + selection + '\\')">📋 Copy</button>';
              showPopup(html, e.pageX, e.pageY);
            }
          });

          document.querySelectorAll('a[href]').forEach(link => {
            link.addEventListener('click', function(e) {
              e.preventDefault();
              const newUrl = this.href;
              window.parent.postMessage({ type: 'navigate', url: newUrl }, '*');
            });
          });
        });
        </script>
        """

        html = re.sub(r"<head.*?>", lambda m: m.group(0) + inject_css + inject_js, html, count=1)

        return Response(html, content_type="text/html")

    except Exception as e:
        return f"Error loading URL: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
