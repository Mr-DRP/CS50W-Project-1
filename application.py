import os
import requests
from flask import Flask, session,render_template,request,redirect,url_for,flash,jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from flask_bcrypt import Bcrypt
#custom decorator
from decorators import login_required

app = Flask(__name__)
bcrypt = Bcrypt(app) #for password hashing

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

#Main search page
@app.route("/")
@login_required
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if 'user_name' in session:
        flash('You are already logged in')
        return redirect(url_for('index'))

    if request.method == "POST":
        # Query database for username
        userCheck = db.execute("SELECT * FROM users WHERE name = :username",
                          {"username":request.form.get("username")}).fetchone()

        # Check if username already exist
        if userCheck:
            return render_template("register.html", message="Username already exist")
        
        # Bcrypt user's password
        pw_hash = bcrypt.generate_password_hash(request.form.get("password")).decode('utf-8')
        
        # Insert register into DB
        db.execute("INSERT INTO users (name, password) VALUES (:username, :password)",
                            {"username":request.form.get("username"), 
                             "password":pw_hash})

        # Commit changes to database
        db.commit()

        # Redirect user to login page
        return redirect(url_for('login_success'))

    # User reached route via GET (as by clicking a link or via redirect)
    return render_template("register.html",message=None)

#Redirect after successful registration
@app.route("/login/success")
def login_success():
    return render_template("login.html", info=True,message=None)

#Login Page
@app.route("/login", methods=["GET", "POST"])
def login():
    if 'user_name' in session:
        flash('You are already logged in')
        return redirect(url_for('index'))

    if request.method == "POST":
        username = request.form.get("username")
        rows = db.execute("SELECT * FROM users WHERE name = :username",
                             {"username": username})
        
        result = rows.fetchone()

        if result and bcrypt.check_password_hash(result[2], request.form.get("password")):
            session["user_id"] = result[0]
            session["user_name"] = result[1]
            return redirect("/")
        else:
            message = "Invalid Credentials!! Try Again"
            return render_template("login.html", message=message,info=None)
    return render_template("login.html",message=None,info=None)

@app.route("/logout")
def logout():
    session.clear()

    return redirect(url_for('login'))


@app.route("/search", methods=["GET"])
@login_required
def search():    
    #Search bar validation
    if not request.args.get("book"):
        return render_template("index.html", message="You can't leave field blank")
    
    #Inserting wildcard to filter result with search term
    search_term = "%" + request.args.get("book").strip() + "%"

    #Capitalize first letter of each word
    query = search_term.title()
    
    rows = db.execute("SELECT isbn, title, author, year FROM book_details WHERE isbn LIKE :query OR title LIKE :query OR author LIKE :query",{"query": query})
    
    #if no records were found
    if rows.rowcount == 0:
        return render_template("index.html", message="Sorry! No book found")
    #test=rows.fetchone()
    #print(test)
    books = rows.fetchall()

    return render_template("search_results.html", books=books,term=request.args.get("book"),length=rows.rowcount)

@app.route("/books/<isbn>", methods=['GET','POST'])
@login_required
def book(isbn):
    if request.method == "POST":
    
        rating = request.form.get("rating")
        comment = request.form.get("text")
        User = session["user_id"]
        
        row = db.execute("SELECT id FROM book_details WHERE isbn = :isbn",{"isbn": isbn})

        book = row.fetchone() 
        print(book.id)

        # Check for user's previous submission
        row2 = db.execute("SELECT * FROM reviews WHERE user_id = :user_id AND book_id = :book_id",
                    {"user_id": User,
                     "book_id": book.id})

        # A review already exists
        if row2.rowcount == 1:
            
            flash('You already submitted a review for this book', 'warning')
            return redirect("/books/" + isbn)

        # Convert to save into DB
        rating = int(rating)

        db.execute("INSERT INTO reviews (user_id, book_id, comment, rating) VALUES \
                    (:user_id, :book_id, :comment, :rating)",
                    {"user_id": User, 
                    "book_id": book.id, 
                    "comment": comment, 
                    "rating": rating})

        db.commit()

        return redirect("/books/" + isbn)

    else:
        row = db.execute("SELECT id, isbn, title, author, year FROM book_details WHERE isbn = :isbn",
                    {"isbn": isbn})

        bookdetails = row.fetchall()
        
        book_id =bookdetails[0][0]
        
        key = os.getenv("GOODREAD_KEY")
        
        query = requests.get("https://www.goodreads.com/book/review_counts.json",params={"key": key, "isbns": isbn})

        # Convert the response to JSON
        response = query.json()

        response = response['books'][0]
        print(response)
    
        avg_rating = response['average_rating']
        total_rating = response['ratings_count']

        results = db.execute("SELECT name, comment, rating FROM users \
                            INNER JOIN reviews ON users.id = reviews.user_id \
                            WHERE book_id = :book \
                            ORDER BY reviews.id DESC",
                            {"book": book_id})

        reviews = results.fetchall()
        
        #For Book cover image
        url = 'https://covers.openlibrary.org/b/isbn/'+isbn+'-M.jpg?default=false'
        r = requests.get(url)
        
        #if no preview available a default image will be used(implemented in template)
        if r.status_code == 404:
            url = None
            
        return render_template(
                            "book_details.html", 
                            bookDetails=bookdetails, reviews=reviews, img_url=url,
                            avg = avg_rating, tot = total_rating)


@app.route("/api/<isbn>", methods=['GET'])
@login_required
def api_call(isbn):
    book = db.execute("SELECT * FROM book_details WHERE isbn = :isbn", {"isbn": isbn}).fetchone()

    #return error if book is not is database
    if book is None:
        return jsonify(
            api_fetch="failed",
            error_message="Invalid ISBN. Try again.")

    row = db.execute("SELECT COUNT(reviews.id) as review_count, \
                     AVG(reviews.rating) as average_score \
                     FROM reviews \
                     WHERE book_id = :id" , {"id": book.id})

    ratings = row.fetchone()
    total_review = ratings[0]
    avg = None if ratings[1]==None else float('%.2f'%(ratings[1])) #format to two place decimal
    return jsonify(
        api_fetch="success",
        title=book.title,
        author=book.author,
        year=book.year,
        isbn=book.isbn,
        review_count=total_review,
        average_count=avg
        )
