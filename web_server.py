


from flask import Flask
from flask import request 
from markupsafe import escape
from search import Search 

search = Search("my_index.json")


web_server = Flask(__name__)
@web_server.route("/")
def DisplaySearch(): 
    page = """
    <form>
    <label for="site-search"> Search ICS: </label>
    <input type = "search" id = "site-search" name = "user_query"/>
    <button>Search</button>
    </form>
    """
    user_query = request.args.get('user_query', '')


    if user_query:
        page += "displaying results for: " + str(escape(user_query)) + "<br>"
        results = search.search(user_query)
        if not results:
            page+=f"No results for {escape(user_query)}"
            return page
        top_results = results[:5]
        for result in top_results:
            page += f'<a href = "{result}">{result}</a><br>'

    
    

    return page  


