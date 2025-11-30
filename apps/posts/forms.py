# apps/posts/forms.py

from django import forms
from .models import Post, Comment, PostReport


class PostCreateForm(forms.ModelForm):
    """Form for creating posts"""

    tags = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Tags (comma separated)'
        }),
        help_text='Enter tags separated by commas'
    )

    class Meta:
        model = Post
        fields = ['content', 'image', 'video', 'post_type', 'is_exclusive', 'tags',
                  'merch_category', 'related_merchandise_id', 'related_event_id']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Share your thoughts...',
                'maxlength': 5000
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'video': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'video/*'
            }),
            'post_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'is_exclusive': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'merch_category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'related_merchandise_id': forms.Select(attrs={
                'class': 'form-select'
            }),
            'related_event_id': forms.Select(attrs={
                'class': 'form-select'
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Make content not required by default (will be validated in clean())
        self.fields['content'].required = False

        # Make new fields optional
        self.fields['merch_category'].required = False
        self.fields['related_merchandise_id'].required = False
        self.fields['related_event_id'].required = False

        # Hide is_exclusive field for non-celebrity users
        if user and hasattr(user, 'user_type') and user.user_type != 'celebrity':
            self.fields.pop('is_exclusive', None)
            # Non-celebrities can't create merch/event posts
            post_type_choices = [choice for choice in Post.POST_TYPES
                                if choice[0] not in ['merch', 'event', 'exclusive']]
            self.fields['post_type'].choices = post_type_choices
            self.fields.pop('merch_category', None)
            self.fields.pop('related_merchandise_id', None)
            self.fields.pop('related_event_id', None)
        else:
            # For celebrities, populate merch and event choices
            from apps.merchandise.models import Merchandise
            from apps.events.models import Event

            # Merch category choices
            MERCH_CATEGORIES = [
                ('', '--- Select Category ---'),
                ('clothing', 'Clothing'),
                ('accessories', 'Accessories'),
                ('collectibles', 'Collectibles'),
                ('digital', 'Digital Products'),
                ('other', 'Other')
            ]
            self.fields['merch_category'].choices = MERCH_CATEGORIES

            # Populate merchandise dropdown if user is celebrity
            if user:
                merch_choices = [('', '--- Select Merchandise ---')]
                user_merch = Merchandise.objects.filter(celebrity=user, status='available')
                merch_choices.extend([(str(m.id), m.name) for m in user_merch])
                self.fields['related_merchandise_id'].widget.choices = merch_choices

                # Populate event dropdown
                event_choices = [('', '--- Select Event ---')]
                user_events = Event.objects.filter(celebrity=user, status='published')
                event_choices.extend([(str(e.id), e.title) for e in user_events])
                self.fields['related_event_id'].widget.choices = event_choices

    def clean_tags(self):
        tags = self.cleaned_data.get('tags', '')
        if tags:
            # Convert comma-separated string to list
            tags_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
            return tags_list
        return []
    
    def clean(self):
        cleaned_data = super().clean()
        content = cleaned_data.get('content', '').strip()
        image = cleaned_data.get('image')
        video = cleaned_data.get('video')

        # At least one of content, image, or video must be provided
        if not content and not image and not video:
            raise forms.ValidationError(
                'Please provide either text content, an image, or a video for your post.'
            )

        # If content is provided, ensure it's not just whitespace
        if content and len(content) < 2:
            raise forms.ValidationError(
                'Post content must be at least 2 characters long.'
            )

        return cleaned_data


class PostEditForm(forms.ModelForm):
    """Form for editing existing posts"""
    
    tags = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Tags (comma separated)'
        }),
        help_text='Enter tags separated by commas'
    )
    
    class Meta:
        model = Post
        fields = ['content', 'image', 'video', 'tags']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Share your thoughts...',
                'maxlength': 5000
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'video': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'video/*'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make all fields optional for editing
        for field in self.fields:
            self.fields[field].required = False
        
        # If instance has tags as a list, convert to comma-separated string
        if self.instance and self.instance.pk:
            if hasattr(self.instance, 'tags') and isinstance(self.instance.tags, list):
                self.initial['tags'] = ', '.join(self.instance.tags)
    
    def clean_tags(self):
        tags = self.cleaned_data.get('tags', '')
        if tags:
            # Convert comma-separated string to list
            tags_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
            return tags_list
        return []


class CommentForm(forms.ModelForm):
    """Form for adding comments"""
    
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Add a comment...',
                'maxlength': 500
            })
        }
    
    def clean_content(self):
        content = self.cleaned_data.get('content', '').strip()
        if not content:
            raise forms.ValidationError('Comment cannot be empty.')
        if len(content) < 2:
            raise forms.ValidationError('Comment must be at least 2 characters long.')
        return content


class CommentEditForm(forms.ModelForm):
    """Form for editing comments"""
    
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Edit your comment...',
                'maxlength': 500
            })
        }
    
    def clean_content(self):
        content = self.cleaned_data.get('content', '').strip()
        if not content:
            raise forms.ValidationError('Comment cannot be empty.')
        if len(content) < 2:
            raise forms.ValidationError('Comment must be at least 2 characters long.')
        return content


class PostReportForm(forms.ModelForm):
    """Form for reporting posts"""
    
    class Meta:
        model = PostReport
        fields = ['reason', 'description']
        widgets = {
            'reason': forms.Select(attrs={
                'class': 'form-select'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Provide additional details (optional)'
            })
        }
    
    def clean_description(self):
        description = self.cleaned_data.get('description', '').strip()
        reason = self.cleaned_data.get('reason')
        
        # Require description for 'other' reason
        if reason == 'other' and not description:
            raise forms.ValidationError(
                'Please provide a description when selecting "Other" as the reason.'
            )
        
        return description


class PostShareForm(forms.Form):
    """Form for sharing/reposting"""
    
    text = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Add your thoughts (optional)...',
            'maxlength': 500
        }),
        help_text='Add a comment to your share'
    )