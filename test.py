todos=[]
while True:
    user_action = input("type add, show, or exit:")
    user_action = user_action.strip()
    match user_action:
        case 'add':
            todo = input("Enter a Todo: ")
            todos.append(todo)
        case 'show':
            for item in todos:
               
                print(item)
        case 'exit':
            break    
               
print('Bye...')    