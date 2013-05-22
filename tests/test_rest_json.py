from tg import TGController
from tgext.crud import EasyCrudRestController
from .base import CrudTest, Movie, DBSession, metadata, Genre, Actor

import transaction

class TestRestJsonEditCreateDelete(CrudTest):
    def controller_factory(self):
        class MovieController(EasyCrudRestController):
            model = Movie

        class RestJsonController(TGController):
            movies = MovieController(DBSession)

        return RestJsonController()

    def test_post(self):
        result = self.app.post('/movies.json', params={'title':'Movie Test'})

        movie = DBSession.query(Movie).first()
        assert movie is not None, result

        assert movie.movie_id == result.json['value']['movie_id']

    def test_post_validation(self):
        result = self.app.post('/movies.json', status=400)
        assert result.json['title'] is not None #there is an error for required title
        assert result.json['description'] is None #there isn't any error for optional description

        assert DBSession.query(Movie).first() is None

    def test_post_validation_dberror(self):
        metadata.drop_all(tables=[Movie.__table__])

        result = self.app.post('/movies.json', params={'title':'Movie Test'}, status=400)
        assert result.json['message'].startswith('(OperationalError)')

    def test_put(self):
        result = self.app.post('/movies.json', params={'title':'Movie Test'})
        movie = result.json['value']

        result = self.app.put('/movies/%s.json' % movie['movie_id'],
                              params={'title':'New Title'})
        assert result.json['value']['title'] == 'New Title'

    def test_put_validation(self):
        result = self.app.post('/movies.json', params={'title':'Movie Test'})
        movie = result.json['value']

        result = self.app.put('/movies/%s.json' % movie['movie_id'],
                              params={'title':''}, status=400)
        assert result.json['title'] is not None #there is an error for required title
        assert result.json['description'] is None #there isn't any error for optional description

        movie = DBSession.query(Movie).first()
        assert movie.title == 'Movie Test'

    def test_delete(self):
        DBSession.add(Movie(title='Fifth Movie'))
        DBSession.flush()
        transaction.commit()

        movie = DBSession.query(Movie).first()

        result = self.app.delete('/movies/%s.json' % movie.movie_id)
        assert result.json == {}

    def test_delete_idempotent(self):
        DBSession.add(Movie(title='Fifth Movie'))
        DBSession.flush()
        transaction.commit()

        movie = DBSession.query(Movie).first()

        result = self.app.delete('/movies/%s.json' % movie.movie_id)
        assert result.json == {}

        result = self.app.delete('/movies/%s.json' % movie.movie_id)
        assert result.json == {}

    def test_delete_nofilter(self):
        DBSession.add(Movie(title='Fifth Movie'))
        DBSession.flush()
        transaction.commit()

        movie = DBSession.query(Movie).first()
        assert movie is not None

        result = self.app.delete('/movies.json')
        assert result.json == {}

        movie = DBSession.query(Movie).first()
        assert movie is not None

class TestRestJsonRead(CrudTest):
    def controller_factory(self):
        class MovieController(EasyCrudRestController):
            model = Movie
            pagination = {'items_per_page': 3}

        class ActorController(EasyCrudRestController):
            model = Actor

        class RestJsonController(TGController):
            movies = MovieController(DBSession)
            actors = ActorController(DBSession)

        return RestJsonController()

    def setUp(self):
        super(TestRestJsonRead, self).setUp()
        genre = Genre(name='action')
        DBSession.add(genre)

        actors = [Actor(name='James Who'), Actor(name='John Doe'), Actor(name='Man Alone')]
        map(DBSession.add, actors)

        DBSession.add(Movie(title='First Movie', genre=genre, actors=actors[:2]))
        DBSession.add(Movie(title='Second Movie', genre=genre, actors=actors[:2]))
        DBSession.add(Movie(title='Third Movie', genre=genre))
        DBSession.add(Movie(title='Fourth Movie', genre=genre))
        DBSession.add(Movie(title='Fifth Movie'))
        DBSession.add(Movie(title='Sixth Movie'))
        DBSession.flush()
        transaction.commit()

    def test_get_all(self):
        result = self.app.get('/movies.json?order_by=movie_id')
        result = result.json['value_list']
        assert result['total'] == 6, result
        assert result['page'] == 1, result
        assert result['entries'][0]['title'] == 'First Movie', result

        result = self.app.get('/movies.json?page=2&order_by=movie_id')
        result = result.json['value_list']
        assert result['total'] == 6, result
        assert result['page'] == 2, result
        assert result['entries'][0]['title'] == 'Fourth Movie', result

    def test_get_all_filter(self):
        actor = DBSession.query(Actor).first()

        result = self.app.get('/actors.json?movie_id=%s' % actor.movie_id)
        result = result.json['value_list']
        assert result['total'] == 2, result

    def test_get_all___json__(self):
        actor = DBSession.query(Actor).filter(Actor.movie_id!=None).first()
        movie_title = actor.movie.title

        result = self.app.get('/actors.json?movie_id=%s' % actor.movie_id)
        result = result.json['value_list']
        assert result['total'] > 0, result

        for entry in result['entries']:
            assert entry['movie_title'] == movie_title

    def test_get_one(self):
        movie = DBSession.query(Movie).first()

        result = self.app.get('/movies/%s.json' % movie.movie_id)
        result = result.json
        assert result['model'] == 'Movie', result
        assert result['value']['title'] == movie.title
        assert result['value']['movie_id'] == movie.movie_id

    def test_get_one___json__(self):
        actor = DBSession.query(Actor).filter(Actor.movie_id!=None).first()
        movie_title = actor.movie.title

        result = self.app.get('/actors/%s.json' % actor.actor_id)
        result = result.json
        assert result['model'] == 'Actor', result
        assert result['value']['name'] == actor.name
        assert result['value']['movie_title'] == movie_title
