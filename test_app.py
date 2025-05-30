import pytest
from app import app, POPULAR_CITIES


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


# Тест: загрузка главной страницы
def test_index_page(client):
    response = client.get('/')
    assert response.status_code == 200
    assert 'Погодное приложение' in response.get_data(as_text=True)


# Тест: автодополнение без запроса (показываем популярные города)
def test_autocomplete_empty_query(client):
    response = client.get('/autocomplete?query=')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == len(POPULAR_CITIES)


# Тест: автодополнение с подстрокой (например "мос")
def test_autocomplete_search_moscow(client):
    response = client.get('/autocomplete?query=мос')
    assert response.status_code == 200
    data = response.get_json()
    assert any('Москва' in city['name'] for city in data)


# Тест: получение погоды по популярному городу (Москва)
def test_get_weather_for_moscow(client):
    response = client.post('/weather', json={'city': 'Москва'})
    assert response.status_code == 200
    data = response.get_json()
    assert 'city' in data
    assert data['city'] == 'Москва'
    assert 'current' in data
    assert 'forecast' in data


# Тест: попытка получить погоду по несуществующему городу
def test_get_weather_for_unknown_city(client):
    response = client.post('/weather', json={'city': 'НесуществующийГород'})
    assert response.status_code == 404
    data = response.get_json()
    assert data['error'] == 'Город не найден'


# Тест: обработка ошибки сервера при неправильном ответе API
def test_weather_api_failure(monkeypatch, client):
    def mock_get_weather_data(*args, **kwargs):
        return None

    monkeypatch.setattr('app.get_weather_data', mock_get_weather_data)

    response = client.post('/weather', json={'city': 'Москва'})
    assert response.status_code == 500
    data = response.get_json()
    assert data['error'] == 'Ошибка получения погоды'


# Тест: ошибка при отсутствии тела запроса
def test_missing_request_body(client):
    response = client.post('/weather')
    assert response.status_code == 400
    data = response.get_json()
    assert data['error'] == 'Город не найден'