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

        if '<head' not in html:
            html = "<html><head></head><body>" + html + "</body></html>"

        inject_css = f"""
        <style>
        body {{
          font-size: 18px !important;
          line-height: 1.6 !important;
          color: #{text_color} !important;
          background-color: #{bg_color} !important;
          word-wrap: break-word !important;
          margin: 0 auto !important;
          padding: 15px;
        }}
        img {{
          max-width: 100% !important;
          height: auto !important;
          object-fit: contain !important;
          display: block;
          margin: 10px 0;
        }}
        #readProgress {{
          position: fixed;
          top: 10px;
          right: 10px;
          background: #0a0;
          color: #fff;
          padding: 10px 15px;
          font-size: 14px;
          border-radius: 8px;
          box-shadow: 0 0 10px #0f0;
          z-index: 999999;
          opacity: 0.65;
        }}
        @media (min-width: 768px) {{
          body {{
            max-width: 900px !important;
            background-color: #{bg_color} !important;
          }}
        }}
        </style>
        """

        inject_js = """
        <script>
        window.addEventListener('DOMContentLoaded', () => {
          const popup = document.createElement('div');
          Object.assign(popup.style, {
            position: 'absolute',
            background: '#222',
            color: '#fff',
            padding: '12px',
            borderRadius: '10px',
            zIndex: 999999,
            maxWidth: '300px',
            fontSize: '16px',
            fontFamily: 'sans-serif',
            display: 'none',
            boxShadow: '0 0 10px #0f0'
          });
          document.body.appendChild(popup);

          function showPopup(html, x, y) {
            popup.innerHTML = html;
            popup.style.left = x + 'px';
            popup.style.top = y + 'px';
            popup.style.display = 'block';
          }

          function hidePopupAfterDelay(ms = 1000) {
            setTimeout(() => popup.style.display = 'none', ms);
          }

          let longPressTimer;
          const startPress = (e) => {
            const touch = e.touches ? e.touches[0] : e;
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
                showPopup(html, touch.pageX, touch.pageY);
              } catch {
                showPopup('⚠️ No dictionary result', touch.pageX, touch.pageY);
              }
            }, 1000);
          };

          const endPress = () => {
            clearTimeout(longPressTimer);
            hidePopupAfterDelay();
          };

          document.addEventListener('mousedown', startPress);
          document.addEventListener('mouseup', endPress);
          document.addEventListener('touchstart', startPress);
          document.addEventListener('touchend', endPress);

          document.addEventListener('dblclick', async e => {
            const word = window.getSelection().toString().trim();
            if (!word) return;
            const res = await fetch('https://api.mymemory.translated.net/get?q=' + encodeURIComponent(word) + '&langpair=en|hi');
            const data = await res.json();
            const translated = data.responseData.translatedText || 'No translation found';
            showPopup('<b>Translation:</b><br>' + translated, e.pageX, e.pageY);
            hidePopupAfterDelay(8000);
          });

          document.addEventListener('mouseup', async e => {
            const selection = window.getSelection().toString().trim();
            if (selection.length > 1) {
              const res = await fetch('https://api.mymemory.translated.net/get?q=' + encodeURIComponent(selection) + '&langpair=en|hi');
              const data = await res.json();
              const translated = data.responseData.translatedText;
              const html = '<b>EN → HI:</b><br>' + translated + '<br><button onclick="navigator.clipboard.writeText(\\'' + selection + '\\')">📋 Copy</button>';
              showPopup(html, e.pageX, e.pageY);
              hidePopupAfterDelay(8000);
            }
          });

          // Reading timer and scroll-based progress
          const progressDiv = document.createElement('div');
          progressDiv.id = 'readProgress';
          document.body.appendChild(progressDiv);

          const words = document.body.innerText.trim().split(/\\s+/).length;
          const wpm = 100;
          const estMinutes = Math.ceil(words / wpm);
          let startTime = Date.now();

          function updateProgress() {
            const elapsed = Math.floor((Date.now() - startTime) / 1000);
            const mins = Math.floor(elapsed / 60);
            const secs = elapsed % 60;
            const percent = Math.floor((window.scrollY + window.innerHeight) / document.body.scrollHeight * 100);
            progressDiv.innerText = `⏱️ ${mins}m ${secs}s /  | 📖 ${percent}%`;
          }
          setInterval(updateProgress, 1000);
          window.addEventListener('scroll', updateProgress);

          // Sync iframe link clicks
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
