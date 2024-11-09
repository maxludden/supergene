
# Super Gene

Welcome to the Super Gene documentation site.

## Search Chapters

<form id="chapter-search-form" action="/search" method="get">
  <label for="chapter-search">Enter Chapter Number:</label>
  <input type="number" id="chapter-search" name="chapter" min="1" required>
  <button type="submit">Search</button>
</form>

## Chapters

<div class="chapters">
  <div class="column">
    {% for chapter in chapters[:chapters|length//3] %}
      <a href="{{ url_for('static', filename='chapters/' ~ chapter) }}">{{ chapter }}</a><br>
    {% endfor %}
  </div>
  <div class="column">
    {% for chapter in chapters[chapters|length//3:2*chapters|length//3] %}
      <a href="{{ url_for('static', filename='chapters/' ~ chapter) }}">{{ chapter }}</a><br>
    {% endfor %}
  </div>
  <div class="column">
    {% for chapter in chapters[2*chapters|length//3:] %}
      <a href="{{ url_for('static', filename='chapters/' ~ chapter) }}">{{ chapter }}</a><br>
    {% endfor %}
  </div>
</div>
