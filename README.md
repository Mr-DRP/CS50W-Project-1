# Project 1

Web Programming with Python and JavaScript

## Login & Register
USer can login using /login and register new account using /register. All the url to different pages will be redirected to login page if user is not already logged in.

## HomePage(search page)
You can search for books using isbn,title,author name or year. This page will return list of books on search.

## Book details page
This page shows details of the books(isbn,author,year, title) along with goodreads average ratings and total number of rating received. This page also allows user to create own review and give ratings to the books.

## API Page 
It can accessed using /api/<isbn> which will return the json as shown below.
```json
{
  "api_fetch": "success",
  "author": "Mary Higgins Clark",
  "average_count": null,
  "isbn": "0743484355",
  "review_count": 0,
  "title": "A Cry in the Night",
  "year": 1982
}

```

### Demo Link: [Click here](https://aflask-book.herokuapp.com/)
### Demo video: [Click here](https://youtu.be/7AlV712CbW8)




