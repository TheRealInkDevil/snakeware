class ElementRegistry:
    def __init__(self):
        self.scopes: dict[str, dict] = {}
        self._active_scopes: list[str] = []
        self._scope_stack: list[str] = []
    
    def create_scope(self, scope_name: str):
        self.scopes.setdefault(scope_name, {})
        self.scopes[scope_name].clear()
    
    def clear_scope(self, scope_name: str):
        self.scopes[scope_name].clear()
    
    def delete_scope(self, scope_name: str):
        del self.scopes[scope_name]

    def push_scope(self, scope_name: str):
        self._scope_stack.append(scope_name)
    
    def pop_scope(self):
        self._scope_stack.pop()
    
    @property
    def current_scope(self):
        return self._scope_stack[-1]
    
    def register(self, name: str, constructor):
        self.scopes[self.current_scope][name] = constructor
    
    def set_active_scopes(self, scopes: list):
        self._active_scopes = scopes.copy()

    def get(self, name):
        for scope in reversed(self._active_scopes):
            if name in self.scopes[scope]:
                return self.scopes[scope][name]
        return None