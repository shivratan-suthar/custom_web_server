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
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" crossorigin="anonymous" referrerpolicy="no-referrer" />
<style>
body, * {{
  font-size: 18px !important;
  line-height: 1.6 !important;
  color: #{text_color} !important;
  background-color: #{bg_color} !important;
  max-width: 100% !important;
  word-wrap: break-word !important;
  box-sizing: border-box;
}}
img {{
  max-width: 100% !important;
  height: auto !important;
}}
#read-stats {{
  position: fixed;
  top: 10px;
  left: 10px;
  background: rgba(0, 0, 0, 0.6);
  color: #0f0;
  font-size: 13px;
  font-family: sans-serif;
  padding: 8px 12px;
  border-radius: 10px;
  z-index: 999999;
  backdrop-filter: blur(5px);
}}
@media (max-width: 600px) {{
  body, * {{
    font-size: 16px !important;
  }}
  #read-stats {{
    font-size: 12px;
    padding: 6px 10px;
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
    maxWidth: '90%',
    fontSize: '15px',
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

  // Translation floating button at top-right
  const translateBtn = document.createElement('button');
  translateBtn.innerHTML = '<i class="fa fa-language"></i> Translate';
  Object.assign(translateBtn.style, {
    position: 'fixed',
    top: '10px',
    right: '10px',
    zIndex: 999999,
    fontSize: '13px',
    padding: '8px 12px',
    background: '#0a0',
    color: '#fff',
    border: 'none',
    borderRadius: '8px',
    boxShadow: '0 0 10px #0f0',
    display: 'none'
  });
  document.body.appendChild(translateBtn);

  document.addEventListener('selectionchange', () => {
    const selection = window.getSelection().toString().trim();
    translateBtn.style.display = (selection.length > 1) ? 'block' : 'none';
  });

  translateBtn.onclick = async () => {
    const selection = window.getSelection().toString().trim();
    const res = await fetch('https://api.mymemory.translated.net/get?q=' + encodeURIComponent(selection) + '&langpair=en|hi');
    const data = await res.json();
    const translated = data.responseData.translatedText;
    showPopup('<b>EN → HI:</b><br>' + translated + '<br><button onclick="navigator.clipboard.writeText(\\'' + translated + '\\')"><i class="fa fa-copy"></i> Copy</button>', 20, 80);
    translateBtn.style.display = 'none';
    hidePopupAfterDelay(8000);
  };

  // Reading stats
  const stats = document.createElement('div');
  stats.id = 'read-stats';
  stats.innerText = 'Reading...';
  document.body.appendChild(stats);

  const startTime = Date.now();
  let prevWordCount = 0;

  setInterval(() => {
    const text = document.body.innerText || '';
    const words = text.split(/\\s+/).filter(w => w.length > 2).length;
    const elapsedMinutes = (Date.now() - startTime) / 60000;
    const wpm = Math.max(1, Math.round(words / elapsedMinutes));
    const remaining = Math.ceil(Math.max(0, (words - prevWordCount)) / Math.max(wpm, 1));
    prevWordCount = words;

    stats.innerText = `Words: ${words} | WPM: ${wpm} | ETA: ${remaining} min`;

    localStorage.setItem('smartReaderHistory', JSON.stringify({
      lastRead: window.location.href,
      wordCount: words,
      timestamp: Date.now()
    }));
  }, 5000);

  // Link sync to parent
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

