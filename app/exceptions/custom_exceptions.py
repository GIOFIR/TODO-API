# app/exceptions/custom_exceptions.py
class TodoNotFoundError(Exception):
    def __init__(self, todo_id: int):
        self.todo_id = todo_id
        super().__init__(f"TODO with id {todo_id} not found")

class DatabaseError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)
