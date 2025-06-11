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

        # Ensure a head tag exists for CSS/JS injection
        if '<head' not in html:
            html = "<html><head></head><body>" + html + "</body></html>"

        inject_css = f"""
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" integrity="sha512-RXf+QSDCUQs6FWLZcZqx/vZr+LRz9vY6XUvOa8j2G6FbAi+cR9Ue2w+u+C5RVkPvXnUZ+RUzRgHQ3yCevG8Nqg==" crossorigin="anonymous" referrerpolicy="no-referrer" />
<style>
body, * {{
  font-size: 18px !important;
  line-height: 1.6 !important;
  color: #{text_color} !important;
  background-color: #{bg_color} !important;
  max-width: 100% !important;
  word-wrap: break-word !important;
  box-sizing: border-box; /* Ensure padding/border don't affect width */
}}
img {{
  max-width: 100% !important;
  height: auto !important;
}}
#read-stats {{
  position: fixed;
  top: 5px;
  right: 5px;
  background: rgba(0, 0, 0, 0.7); /* Added transparency */
  color: #0f0;
  font-size: 12px;
  font-family: sans-serif;
  padding: 6px 10px;
  border-radius: 10px;
  z-index: 999999;
}}
#translate-popup {{ /* Styles for the translate selection popup */
  position: absolute;
  background: rgba(34, 34, 34, 0.9); /* Added transparency */
  color: #fff;
  padding: 12px;
  border-radius: 10px;
  z-index: 999999;
  max-width: 300px;
  font-size: 15px;
  font-family: sans-serif;
  display: none;
  box-shadow: 0 0 10px #0f0;
}}

/* Responsive adjustments for smaller screens */
@media (max-width: 768px) {
  body, * {{
    font-size: 16px !important;
  }}
  #read-stats {{
    font-size: 10px;
    padding: 4px 8px;
    top: 2px;
    right: 2px;
  }}
  #translate-popup {{
    max-width: 90%;
    left: 5% !important; /* Center on mobile */
    right: 5% !important;
    transform: translateX(0) !important;
  }}
}
</style>
"""

        inject_js = """
<script>
window.addEventListener('DOMContentLoaded', () => {
  const popup = document.createElement('div');
  popup.id = 'translate-popup'; // Assign ID for styling
  document.body.appendChild(popup);

  function showPopup(html, x, y) {
    popup.innerHTML = html;
    // Adjust position to stay within viewport, especially on smaller screens
    const viewportWidth = window.innerWidth || document.documentElement.clientWidth;
    const viewportHeight = window.innerHeight || document.documentElement.clientHeight;
    
    let left = x;
    let top = y;

    // Check if popup goes off screen to the right
    if (x + popup.offsetWidth > viewportWidth - 20) {
      left = viewportWidth - popup.offsetWidth - 20;
    }
    // Check if popup goes off screen to the bottom
    if (y + popup.offsetHeight > viewportHeight - 20) {
      top = viewportHeight - popup.offsetHeight - 20;
    }
    // Ensure it doesn't go off screen to the left or top
    if (left < 10) left = 10;
    if (top < 10) top = 10;

    popup.style.left = left + 'px';
    popup.style.top = top + 'px';
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
  document.addEventListener('touchstart', startPress, { passive: true }); // Use passive for touch events
  document.addEventListener('touchend', endPress);

  // Translate on selection (modified to show at top)
  document.addEventListener('mouseup', async e => {
    const selection = window.getSelection().toString().trim();
    if (selection.length > 1) {
      const res = await fetch('https://api.mymemory.translated.net/get?q=' + encodeURIComponent(selection) + '&langpair=en|hi');
      const data = await res.json();
      const translated = data.responseData.translatedText;
      const html = '<b>EN → HI:</b><br>' + translated +
        '<br><button onclick="navigator.clipboard.writeText(\\' ' + translated.replace(/'/g, "\\'") + '\\')"><i class="fa fa-copy"></i> Copy</button>';
      
      // Position at the top, just below the stats bar
      showPopup(html, e.pageX, 50); // Adjust Y coordinate as needed
      hidePopupAfterDelay(8000);
    }
  });

  // Reading stats
  const stats = document.createElement('div');
  stats.id = 'read-stats';
  stats.innerText = 'Initializing...';
  document.body.appendChild(stats);

  let totalWords = 0;
  let wordsReadInInterval = 0;
  let previousScrollY = 0;
  const wordReadHistory = []; // To store (timestamp, words_read_since_last_check)
  const intervalDuration = 3000; // 3 seconds for updating stats

  // Function to calculate words visible in the viewport
  function countVisibleWords() {
    let visibleWords = 0;
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const text = entry.target.innerText;
          visibleWords += text.split(/\\s+/).filter(w => w.length > 2).length;
        }
      });
    }, { threshold: 0.1 }); // Trigger when 10% of the element is visible

    // Observe all text-containing elements (p, div, span, etc.)
    document.querySelectorAll('p, div, span, h1, h2, h3, h4, h5, h6, li').forEach(element => {
      if (element.children.length === 0 && element.innerText.trim().length > 0) { // Only observe leaf nodes with text
        observer.observe(element);
      }
    });
    return visibleWords;
  }

  // Initial total words calculation
  totalWords = (document.body.innerText || '').split(/\\s+/).filter(w => w.length > 2).length;

  setInterval(() => {
    const currentScrollY = window.scrollY;
    
    // Estimate words read by scrolling
    if (currentScrollY > previousScrollY) {
      // Simple heuristic: Assume reading down the page. This is a rough estimate.
      // A more accurate WPM needs to track *which* words have been scrolled past.
      // For now, let's use the delta scroll to estimate reading progress.
      // This is a common simplification for WPM in browser-based readers.
      const scrollDelta = currentScrollY - previousScrollY;
      // This factor might need tuning based on average line height and font size.
      // Roughly, assume 10 words per 50 pixels of scroll.
      wordsReadInInterval += Math.round(scrollDelta / 50 * 10); 
    }
    previousScrollY = currentScrollY;

    // Filter out words that are too small or just punctuation
    const wordsInBody = (document.body.innerText || '').split(/\\s+/).filter(w => w.length > 2);
    const currentTotalWords = wordsInBody.length;

    // We'll use the *current viewable words* as our baseline for "words remaining"
    // and attempt to calculate WPM based on *accumulated* words read.

    // A more accurate WPM is based on *actual words read*, not total words in document.
    // For a proxy, this is tricky. We'll use the scroll-based estimation, but acknowledge its limitations.

    const now = Date.now();
    wordReadHistory.push({ time: now, words: wordsReadInInterval });

    // Keep history for the last 60 seconds (or more if needed for smoother average)
    const historyDuration = 60000; 
    while (wordReadHistory.length > 1 && (now - wordReadHistory[0].time > historyDuration)) {
      wordReadHistory.shift();
    }

    // Calculate WPM from history
    let totalWordsInHistory = 0;
    if (wordReadHistory.length > 1) {
      totalWordsInHistory = wordReadHistory[wordReadHistory.length - 1].words - wordReadHistory[0].words;
    }
    
    const timeElapsedInHistory = (wordReadHistory[wordReadHistory.length - 1].time - wordReadHistory[0].time) / 1000; // seconds

    let wpm = 0;
    if (timeElapsedInHistory > 0) {
      wpm = Math.round((totalWordsInHistory / timeElapsedInHistory) * 60);
    }
    
    // Set a minimum reasonable WPM to avoid division by zero or inflated ETAs
    const effectiveWpm = Math.max(wpm, 150); // A reasonable floor for reading speed

    // Calculate words remaining based on total document words (simplified)
    const wordsRemaining = Math.max(0, currentTotalWords - wordsReadInInterval);
    const timeRemainingMinutes = wordsRemaining / effectiveWpm;
    
    stats.innerText = `Words: ${currentTotalWords} | WPM: ${wpm} | ETA: ${Math.ceil(timeRemainingMinutes)} min`;

    localStorage.setItem('smartReaderHistory', JSON.stringify({
      lastRead: window.location.href,
      wordCount: currentTotalWords,
      timestamp: Date.now()
    }));
  }, intervalDuration); // Update every 3 seconds

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
