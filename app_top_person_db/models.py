from django.db import models
from django.db import models
import ast

class TopPerson(models.Model):
    category = models.CharField(max_length=100)
    top_keys = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.category}: {self.top_keys}"
    
    def get_top_keys_as_list(self):
        """Convert the string representation of top_keys to a Python list of tuples"""
        try:
            return ast.literal_eval(self.top_keys)
        except:
            return []

'''
是 Python 的 Abstract Syntax Trees（抽象語法樹）模組。
ast.literal_eval() 可以安全地將字串（如 '[("A", 1), ("B", 2)]'）轉換成對應的 Python 物件（如 list、dict、tuple 等），但只允許字面值（literal），不會執行任意程式碼，比 eval() 更安全。

你可以用純 Python 內建函式 eval() 達到類似效果，但這樣有安全風險，因為 eval() 會執行字串中的任何 Python 程式碼，容易被惡意利用。
s = '[("A", 1), ("B", 2)]'
lst = ast.literal_eval(s)  # 安全，僅允許字面值

# 不建議這樣做
lst2 = eval(s)  # 不安全，可能執行惡意程式碼


字面值（literal）是指在程式碼中直接寫出來、代表固定值的資料。
常見的字面值有：

數字：1, 3.14
字串："hello", 'abc'
布林值：True, False
容器類型：[1, 2, 3]（list）、{"a": 1}（dict）、("A", 1)（tuple）
例如，[("A", 1), ("B", 2)] 這個字串就是一個 list 的字面值。
字面值不包含變數、函式呼叫或運算式，只是單純的資料本身。

'''


'''
# To create the database table for the TopPerson model, you need to run the following commands in your terminal:
python manage.py makemigrations app_top_person_db
python manage.py migrate
'''

