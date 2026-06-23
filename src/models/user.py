"""Authenticated user assembled from Keycloak token claims."""


class User:
    def __init__(self, id, username, email, group, first_name, last_name, realm_roles, client_roles):
        self.id = id
        self.username = username
        self.email = email
        self.group = group
        self.first_name = first_name
        self.last_name = last_name
        self.realm_roles = realm_roles
        self.client_roles = client_roles

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'group': self.group,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'realm_roles': self.realm_roles,
            'client_roles': self.client_roles
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)
