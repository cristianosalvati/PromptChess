import mysql.connector
from datetime import datetime

class DbConnector:
    # "Classe per gestire la connessione e le query al database."

    def __init__(self, config):
        message = "Inizializza la connessione con i dettagli di configurazione."
        print(message)
        self.connection_config = config['persistence']['connection']
        self.queries = config['persistence']['named_queries']
        self.conn = None
        self.cursor = None

    def get_query_by_name(self, query_name):
        message = "Recupera una query dal dizionario."
        print(message)
        return self.queries[query_name]

    def connect(self):
        message = "Crea una connessione al database."
        print(message)
        self.conn = mysql.connector.connect(
            host=self.connection_config['host'],
            port=self.connection_config['port'],
            user=self.connection_config['user'],
            password=self.connection_config['password'],
            database=self.connection_config['schema']
        )
        self.cursor = self.conn.cursor(dictionary=True)

    def execute_named_query(self, query_name, params):
        message = "Esegue una query recuperata nel dizionario con parametri forniti."
        print(message)
        print(f"Eseguo la query con nome: {query_name}")
        query = self.queries[query_name]
        self.cursor.execute(query, params)
        print(f"excetuted query: {query}")
        return self.cursor.fetchall()

    def execute_any_query(self, query, params):
        message = f"Esegue una query dinamica, {query} con parametri forniti: {params}"
        print(message)
        cursor = self.conn.cursor(dictionary=True)
        cursor.execute(query, params)
        result = cursor.fetchall()
        cursor.close()
        print(f"excetuted query: {query}, returning: {result}")
        return result

    def execute_update_query(self, query_name, params):
        message = f"Esegue una query di tipo UPDATE o INSERT. {query_name} con parametri forniti: {params}"
        print(message)
        try:  
            self.ensure_connection()  # Assicurati che la connessione sia valida
            query = self.queries[query_name]
            self.cursor.execute(query, params)
            self.conn.commit()  # Fai il commit delle modifiche
            print(f"excetuted query: {query}")
        except Exception as e:
            self.conn.rollback()  # Rollback in caso di errore
            raise e

    def ensure_connection(self):
        """Verifica lo stato della connessione e la ricrea se necessario."""
        try:
            if self.conn is None or not self.conn.is_connected():
                print(f"Connessione al database non attiva. Riconnessione...")
                self.connect()
        except mysql.connector.Error as err:
            print(f"Errore durante il tentativo di riconnessione: {err}")
            raise


    def close(self):
        message = "Chiude il cursore e la connessione."
        print(message)
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
