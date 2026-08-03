# Commands
```
python3 -m http.server 8000
```
The above created a minimal web server to test out the website.
Use this command for automatic refresh:
```
livereload .
```
Need to install python virtual env with ```python3 -m venv venv```, and ```pip install livereload .```

The following command minifies the css:
```
npx clean-css-cli assets/css/style.css -o assets/css/style.min.css
```

# Thoughts
- If I add an author field, I can repost or republish bits by others either with permission or openly for public domain content
  - This could make it easier to link to things within the site
  - I can also directly link to sources too
- Maybe a lists page? Of other blogs etc I find intersting
  - Where to put it? "Cool Stuff"? or "Check this out"?

# Sources
- Example `build-site.sh` code from https://github.com/JurrianFahner/ssg-pandoc
