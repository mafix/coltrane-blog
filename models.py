"""
Models for a weblog application.

"""


import datetime

from comment_utils.managers import CommentedObjectManager
from comment_utils.moderation import CommentModerator, moderator
from django.conf import settings
from django.db import models
from django.utils.encoding import smart_str
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.comments import models as comment_models
from tagging.fields import TagField
from template_utils.markup import formatter

from coltrane import managers


class Category(models.Model):
    """
    A category that an Entry can belong to.
    
    """
    title = models.CharField(maxlength=250)
    slug = models.SlugField(prepopulate_from=('title',), unique=True,
                            help_text=u'Used in the URL for the category. Must be unique.')
    description = models.TextField(help_text=u'A short description of the category, to be used in list pages.')
    description_html = models.TextField(editable=False, blank=True)
    
    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['title']
    
    class Admin:
        pass
    
    def __unicode__(self):
        return self.title
    
    def save(self):
        self.description_html = formatter(self.description)
        super(Category, self).save()
    
    def get_absolute_url(self):
        return ('coltrane_category_detail', (), { 'slug': self.slug })
    get_absolute_url = models.permalink(get_absolute_url)
    
    def _get_live_entries(self):
        """
        Returns Entries in this Category with status of "live".
        
        Access this through the property ``live_entry_set``.
        
        """
        return self.entry_set.filter(status__exact=1)
    
    live_entry_set = property(_get_live_entries)


class Entry(models.Model):
    """
    An entry in the weblog.
    
    Slightly denormalized, because it uses two fields each for the
    excerpt and the body: one for the actual text the user types in,
    and another to store the HTML version of the Entry (e.g., as
    generated by a text-to-HTML converter like Textile or Markdown).
    This saves having to run the conversion each time the Entry is
    displayed.
    
    Entries can be grouped by categories or by tags or both, or not
    grouped at all.
    
    """
    STATUS_CHOICES = (
        (1, 'Live'),
        (2, 'Draft'),
        (3, 'Hidden'),
        )
    
    # Metadata.
    author = models.ForeignKey(User)
    enable_comments = models.BooleanField(default=True)
    featured = models.BooleanField(default=False)
    pub_date = models.DateTimeField(u'Date posted', default=datetime.datetime.today)
    slug = models.SlugField(prepopulate_from=('title',),
                            unique_for_date='pub_date',
                            help_text=u'Used in the URL of the entry. Must be unique for the publication date of the entry.')
    status = models.IntegerField(choices=STATUS_CHOICES, default=1,
                                 help_text=u'Only entries with "live" status will be displayed publicly.')
    title = models.CharField(maxlength=250)
    
    # The actual entry bits.
    body = models.TextField()
    body_html = models.TextField(editable=False, blank=True)
    excerpt = models.TextField(blank=True, null=True)
    excerpt_html = models.TextField(blank=True, null=True, editable=False)
    
    # Categorization.
    categories = models.ManyToManyField(Category, filter_interface=models.HORIZONTAL, blank=True)
    tags = TagField()
    
    # Managers.
    objects = models.Manager()
    live = managers.LiveEntryManager()
    
    class Meta:
        get_latest_by = 'pub_date'
        ordering = ['-pub_date']
        verbose_name_plural = 'Entries'
    
    class Admin:
        date_hierarchy = 'pub_date'
        fields = (
            ('Metadata', { 'fields':
                           ('title', 'slug', 'pub_date', 'author', 'status', 'featured', 'enable_comments') }),
            ('Entry', { 'fields':
                        ('excerpt', 'body') }),
            ('Categorization', { 'fields':
                                 ('tags', 'categories') }),
            )
        list_display = ('title', 'pub_date', 'author', 'status', 'enable_comments', '_get_comment_count')
        list_filter = ('status', 'categories')
        search_fields = ('excerpt', 'body', 'title')
    
    def __unicode__(self):
        return self.title
    
    def save(self):
        if self.excerpt:
            self.excerpt_html = formatter(self.excerpt)
        self.body_html = formatter(self.body)
        super(Entry, self).save()
        
    def get_absolute_url(self):
        return ('coltrane_entry_detail', (), { 'year': self.pub_date.strftime('%Y'),
                                               'month': self.pub_date.strftime('%b').lower(),
                                               'day': self.pub_date.strftime('%d'),
                                               'slug': self.slug })
    get_absolute_url = models.permalink(get_absolute_url)
    
    def _next_previous_helper(self, direction):
        return getattr(self, 'get_%s_by_pub_date' % direction)(status__exact=1)
    
    def get_next(self):
        """
        Returns the next Entry with "live" status by ``pub_date``, if
        there is one, or ``None`` if there isn't.
        
        In public-facing views and templates, use this method instead
        of ``get_next_by_pub_date``, because ``get_next_by_pub_date``
        cannot differentiate live Entries.
        
        """
        return self._next_previous_helper('next')
    
    def get_previous(self):
        """
        Returns the previous Entry with "live" status by ``pub_date``,
        if there is one, or ``None`` if there isn't.
        
        In public-facing views and templates, use this method instead
        of ``get_previous_by_pub_date``, because
        ``get_previous_by_pub_date`` cannot differentiate live Entries.
        
        """
        return self._next_previous_helper('previous')

    def _get_comment_count(self):
        model = settings.USE_FREE_COMMENTS and comment_models.FreeComment or comment_models.Comment
        ctype = ContentType.objects.get_for_model(self)
        return model.objects.filter(content_type__pk=ctype.id, object_id__exact=self.id).count()
    _get_comment_count.short_description = 'Number of comments'


class Link(models.Model):
    """
    A link posted to the weblog.
    
    Denormalized in the same fashion as the Entry model, in order to
    allow text-to-HTML conversion to be performed on the
    ``description`` field.
    
    """
    # Metadata.
    enable_comments = models.BooleanField(default=True)
    post_elsewhere = models.BooleanField(u'Post to del.icio.us',
                                         default=settings.DEFAULT_EXTERNAL_LINK_POST,
                                         help_text=u'If checked, this link will be posted both to your weblog and to your del.icio.us account.')
    posted_by = models.ForeignKey(User)
    pub_date = models.DateTimeField(default=datetime.datetime.today)
    slug = models.SlugField(prepopulate_from=('title',),
                            unique_for_date='pub_date',
                            help_text=u'Must be unique for the publication date.')
    title = models.CharField(maxlength=250)
    
    # The actual link bits.
    description = models.TextField(blank=True, null=True)
    description_html = models.TextField(editable=False, blank=True, null=True)
    via_name = models.CharField(u'Via', maxlength=250, blank=True, null=True,
                                help_text=u'The name of the person whose site you spotted the link on. Optional.')
    via_url = models.URLField('Via URL', verify_exists=False, blank=True, null=True,
                              help_text=u'The URL of the site where you spotted the link. Optional.')
    tags = TagField()
    url = models.URLField('URL', unique=True, verify_exists=False)
    
    objects = CommentedObjectManager()
    
    class Meta:
        get_latest_by = 'pub_date'
        ordering = ['-pub_date']
    
    class Admin:
        date_hierarchy = 'pub_date'
        fields = (
            ('Metadata', { 'fields':
                           ('title', 'slug', 'pub_date', 'posted_by', 'enable_comments', 'post_elsewhere') }),
            ('Link', { 'fields':
                      ('url', 'description', 'tags', 'via_name', 'via_url') }),
            )
        list_display = ('title', 'enable_comments')
        search_fields = ('title', 'description')
    
    def __unicode__(self):
        return self.title
    
    def save(self):
        if not self.id and self.post_elsewhere:
            import pydelicious
            try:
                pydelicious.add(settings.DELICIOUS_USER, settings.DELICIOUS_PASSWORD, smart_str(self.url), smart_str(self.title), smart_str(self.tags))
            except:
                pass # TODO: don't just silently quash a bad del.icio.us post
        if self.description:
            self.description_html = formatter(self.description)
        super(Link, self).save()
    
    def get_absolute_url(self):
        return ('coltrane_link_detail', (), { 'year': self.pub_date.strftime('%Y'),
                                              'month': self.pub_date.strftime('%b').lower(),
                                              'day': self.pub_date.strftime('%d'),
                                              'slug': self.slug })
    get_absolute_url = models.permalink(get_absolute_url)


class ColtraneModerator(CommentModerator):
    akismet = True
    auto_moderate_field = 'pub_date'
    email_notification = True
    enable_field = 'enable_comments'
    moderate_after = settings.COMMENTS_MODERATE_AFTER

moderator.register([Entry, Link], ColtraneModerator)
