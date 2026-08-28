import tkinter as tk

root= tk. Tk()
root.title("대화창")
root.geometry("350x250")

name="Kelly"
conversation = f"""Hello, Jake
Hi, Mrs. Ellen
Who's next to you?
Nice to meet you, {name}"""

label = tk. Label(root, text=conversation, font=("맑은 고딕", 12), justify="left")
label.pack(pady=20)

button = tk. Button(root, text="닫기", command=root.destroy, width=10)
button.pack()

root.mainloop()