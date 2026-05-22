class Book:
    def __init__(self, book_id, title, author):
        self.book_id = book_id
        self.title = title
        self.author = author
        self.is_borrowed = False


class User:
    def __init__(self, user_id, name):
        self.user_id = user_id
        self.name = name
        self.borrowed_books = []

    def borrow_book(self, book):
        if not book.is_borrowed:
            book.is_borrowed = True
            self.borrowed_books.append(book)
            return f"Book '{book.title}' borrowed by {self.name}."
        else:
            return f"Book '{book.title}' is already borrowed."

    def return_book(self, book):
        if book in self.borrowed_books:
            book.is_borrowed = False
            self.borrowed_books.remove(book)
            return f"Book '{book.title}' returned by {self.name}."
        else:
            return f"Book '{book.title}' was not borrowed by {self.name}."


class Transaction:
    def __init__(self, user, book, action):
        self.user = user
        self.book = book
        self.action = action


class Library:
    def __init__(self):
        self.books = {}
        self.users = {}
        self.transactions = []

    def add_book(self, book_id, title, author):
        if book_id not in self.books:
            self.books[book_id] = Book(book_id, title, author)
            return f"Book '{title}' added to the library."
        else:
            return f"Book ID {book_id} already exists."

    def add_user(self, user_id, name):
        if user_id not in self.users:
            self.users[user_id] = User(user_id, name)
            return f"User '{name}' added to the library."
        else:
            return f"User ID {user_id} already exists."

    def borrow_book(self, user_id, book_id):
        if user_id in self.users and book_id in self.books:
            user = self.users[user_id]
            book = self.books[book_id]
            message = user.borrow_book(book)

            if "borrowed" in message:
                self.transactions.append(Transaction(user, book, "borrow"))

            return message
        else:
            return "User ID or Book ID not found."

    def return_book(self, user_id, book_id):
        if user_id in self.users and book_id in self.books:
            user = self.users[user_id]
            book = self.books[book_id]
            message = user.return_book(book)

            if "returned" in message:
                self.transactions.append(Transaction(user, book, "return"))

            return message
        else:
            return "User ID or Book ID not found."