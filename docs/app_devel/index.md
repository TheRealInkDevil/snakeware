# Snakeware App Development
## Entrypoints
Snakeware Apps can have three kinds of entrypoints:
1. ClassEntry
2. FuncEntry
3. PageEntry
### ClassEntry
Snakeware will create an instance of a class from your app module (inherited from swapp.App) and dispatch events to it. Execution is controlled by your App class and Snakeware app events.
### FuncEntry
Snakeware will execute a function from your app module. Your app exits when the code finishes. Execution is controlled by your app.
### PageEntry
Snakeware will parse and render a swpage3 page directly. Execution is controlled by Snakeware and any created elements.
**(NOT RECOMMENDED, MAY BE REMOVED FROM SNAKEWARE IN THE NEAR FUTURE)**