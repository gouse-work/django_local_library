import datetime
import uuid

from django.test import TestCase
from django.urls import reverse
from catalog.models import Author,BookInstance,Book,Genre,Language
from django.contrib.auth.models import User
from django.utils import timezone
from django.contrib.auth.models import Permission

class AuthorListViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        number_of_authors=13
        for author_id in range(number_of_authors):
            Author.objects.create(
                first_name=f'Christian {author_id}',
                last_name=f'Surname {author_id}'
            )

    def test_view_url_exists_at_desired_location(self):
        response=self.client.get('/catalog/authors/')
        self.assertEqual(response.status_code,200)

    def test_view_url_accessible_by_name(self):
        response=self.client.get(reverse('authors'))
        self.assertEqual(response.status_code,200)

    def test_view_uses_correct_template(self):
        response=self.client.get(reverse('authors'))
        self.assertEqual(response.status_code,200)
        self.assertTemplateUsed(response,'catalog/author_list.html')

    def test_pagination_is_ten(self):
        response=self.client.get(reverse('authors'))
        self.assertEqual(response.status_code,200)
        self.assertTrue('is_paginated' in response.context)
        self.assertTrue(response.context['is_paginated']==True)
        self.assertEqual(len(response.context['author_list']),10)

    def test_list_all_authors(self):
        response=self.client.get(reverse('authors')+'?page=2')
        self.assertEqual(response.status_code,200)
        self.assertTrue('is_paginated' in response.context)
        self.assertTrue(response.context['is_paginated']==True)
        self.assertEqual(len(response.context['author_list']),3)


class LoanedBookInstancesByUserListViewTest(TestCase):
    def setUp(self):
        test_user1=User.objects.create_user(username='testuser1',password='1X<ISRUkw+tuK')
        test_user2=User.objects.create_user(username='testuser2',password='2HJ1vRV0Z&3iD')

        test_user1.save()
        test_user2.save()

        test_author=Author.objects.create(first_name='John',last_name='Smith')
        test_genre=Genre.objects.create(name='Fantasy')
        test_language=Language.objects.create(name='English')

        test_book=Book.objcts.create(
            title='Book Title',
            summary='My book',
            isbn='ABCDEFG',
            author=test_author,
            language=test_language
        )

        genre_objects_for_book=Genre.objects.all()
        test_book.genre.set(genre_objects_for_book)
        test_book.save()

        number_of_book_copies=30
        for book_copy in range(number_of_book_copies):
            return_date=timezone.localtime()+datetime.timedelta(days=book_copy/5)
            the_borrower=test_user1 if book_copy%2 else test_user2
            status='m'
            BookInstance.objects.create(
                book=test_book,
                imprint='unlikely imprint,2016',
                due_back=return_date,
                the_borrower=the_borrower,
                status=status
            )

    def test_redirect_if_not_logged_in(self):
        response=self.client.get(reverse('my-borrowed'))
        self.assertRedirects(response,'/accounts/login/?next=/catalog/mybooks/')

    def test_logged_in_uses_correct_template(self):
        login=self.client.login(username='testuser1',password='1X<ISRUkw+tuK')
        response=self.client.get(reverse('my-borrowed'))

        self.assertEqual(str(response.context['user']),'testuser1')
        self.assertEqual(response.status_code,200)
        self.assertTemplateUsed(response,'catalog/bookinstance_list_borrowed_user.html')

    def test_onlu_borrowed_books_in_list(self):
        login=self.client.login(username='testuser1',password='1X<ISRUkw+tuK')
        response=self.client.get(reverse('my-borrowed'))

        self.assertEqual(response.context['user'],'testuser1')
        self.assertEqual(response.status_code,200)
        self.assertTrue('bookinstance_list' in response.context)

        for book_item in response.context['bookinstance_list']:
            self.assertEqual(response.context['user'],book_item.borrower)
            self.assertEqual(book_item.status,'o')

    def test_pages_ordered_by_due_date(self):
        for book in BookInstance.objects.all():
            book.status='o'
            book.save()

        login=self.client.login(username='testuser1',password='1X<ISRUkw+tuK')
        response=self.client.get(reverse('my-borrowed'))

        self.assertEqual(response.context['user'],'testuser1')
        self.assertEqual(response.status_code,200)

        self.assertEqual(len(response.context['bookinstance_list']),10)

        last_date=0

        for book in response.context['bookinstance_list']:
            if last_date==0:
                last_date=book.due_back

            else:
                self.assertTrue(last_date<=book.due_back)
                last_date=book.due_back


class RenewBookInstancesViewTest(TestCase):
    def setUp(self):
        test_user1=User.objects.create(username='testuser1', password='1X<ISRUkw+tuK')
        test_user2=User.objects.create(username='testuser2', password='2HJ1vRV0Z&3iD')

        test_user1.save()
        test_user2.save()

        permission=Permission.objects.get(name='Set book as returned')
        test_user2.user_permissions.add(permission)
        test_user2.save()

        test_author=Author.objects.create(first_name='John',last_name='Smith')
        test_genre=Genre.objects.create(name='Fantasy')
        test_language=Language.objects.create('English')
        test_book=Book.objects.create(
            author=test_author,
            title='Book Title',
            summry='My book summary',
            isbn='ABCDEFG',
            language=test_language
        )
        genre_objects_for_book=Genre.objects.all()
        test_book.genre.set(genre_objects_for_book)
        test_book.save()

        return_date=datetime.date.today()+datetime.timedelta(days=5)
        self.test_bookinstance1=BookInstance.objects.create(
            book=test_book,
            imprint='Unlikely imprint,2016',
            due_back=return_date,
            borrower=test_user1,
            status='o'

        )
        self.test_bookinstance2=BookInstance.objects.create(
            book=test_book,
            imprint='Unlikely imprint,2016',
            due_back=return_date,
            borrower=test_user2,
            status='o'
        )

    def test_redirect_if_not_logged_in(self):
        response=self.client.get(reverse('renew-book-librarian',kwargs={'pk':self.test_bookinstance1.pk}))
        self.assertEqual(response.status_code,302)
        self.assertTrue(response.url.startswith('/accounts/login/'))

    def test_forbidden_if_logged_in_but_not_correct_permission(self):
        login=self.client.login(username='testuser1', password='1X<ISRUkw+tuK')
        response=self.client.get(reverse('renew-book-librarian',kwargs={'pk':self.test_bookinstance1.pk}))
        self.assertTrue(response.status_code,403)

    def test_logged_in_with_permission_borrowed_book(self):
        login=self.client.login(username='testuser2', password='2HJ1vRV0Z&3iD')
        response=self.client.get(reverse('renew-book-librarian',kwargs={'pk':self.test_bookinstance2.pk}))
        self.assertEqual(response.status_code,200)

    def test_logged_in_with_permission_another_user_borrowed_book(self):
        login=self.client.login(username='testuser2', password='2HJ1vRV0Z&3iD')
        response=self.client.get(reverse('renew-book-librarian',kwargs={'pk':self.test_bookinstance1.pk}))
        self.assertEqual(response.status_code,200)

    def test_HTTP404_for_invalid_book_if_logged_in(self):
        test_uuid=uuid.uuid4()
        login=self.client.login(username='testuser2', password='2HJ1vRV0Z&3iD')
        response=self.client.get(reverse('renew-book-librarian',kwargs={'pk':test_uuid}))
        self.assertEqual(response.status_code,404)


    def test_uses_correct_template(self):
        login=self.client.login(username='testuser2', password='2HJ1vRV0Z&3iD')
        response=self.client.get(reverse('renew-book-librarian',kwargs={'pk':self.test_bookinstance2.pk}))
        self.assertEqual(response.status_code,200)
        self.assertTemplateUsed(response,'catalog/book_renew_librarian.html')

    def test_form_renewal_date_initially_has_date_three_weeks_in_future(self):
        login=self.client.login(username='testuser2', password='2HJ1vRV0Z&3iD')
        response=self.client.get(reverse('renew-book-librarian',kwargs={'pk':self.test_bookinstance2.pk}))
        self.assertEqual(response.status_code,200)
        date_3_weeks_in_future=datetime.date.today()+datetime.timedelta(weeks=3)
        self.assertEqual(response.context['form'].initial['renewal_date'],date_3_weeks_in_future)

    def test_redirects_to_all_borrowed_books_list_on_success(self):
        login=self.client.login(username='testuser2', password='2HJ1vRV0Z&3iD')
        valid_date_in_future=datetime.date.today()+datetime.timedelta(weeks=2)
        response=self.client.post(reverse('renew-book-librarian',kwargs={'pk':self.test_bookinstance1.pk}),{'renewal_date':valid_date_in_future})
        self.assertRedirects(response,reverse('all-borrowed'))

    def test_form_invalid_renewal_date_past(self):
        login=self.client.login(username='testuser2', password='2HJ1vRV0Z&3iD')
        date_in_past=datetime.date.today()-datetime.timedelta(weeks=1)
        response=self.client.post(reverse('renew-book-librarian',kwargs={'pk':self.test_bookinstance1.pk}),{'renewal_date':date_in_past})
        self.assertEqual(response.status_code,200)
        self.assertFormError(response,'form','renewal_date','Invalid date - renewal in past')

    def test_form_invalid_renewal_date_future(self):
        login=self.client.login(username='testuser2', password='2HJ1vRV0Z&3iD')
        invalid_date_in_future=datetime.date.today()+datetime.timedelta(weeks=5)
        response=self.client.post(reverse('renew-book-librarian',kwargs={'pk':self.test_bookinstance1.pk}),{'renewal_date':invalid_date_in_future})
        self.assertEqual(response.status_code,200)
        self.assertFormError(response,'form','renewal_date','Invalid date - renewal more than 4 weeks ahead')

