from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Post, Comment, User
from app.forms import PostForm
from sqlalchemy import desc


community = Blueprint('community', __name__)

@community.route('/community')
def community_get():
    search_query = request.args.get('search', '')
    if search_query:
        posts = Post.query.filter(
            (Post.title.ilike(f'%{search_query}%')) | 
            (Post.content.ilike(f'%{search_query}%')) | 
            (Post.author.has(User.username.ilike(f'%{search_query}%')))
        ).order_by(Post.date_posted.desc()).all()
    else:
        posts = db.session.query(Post).order_by(Post.date_posted.desc()).all()
    return render_template('community.html', posts=posts)

@community.route('/community/<post_id>', methods=['GET', 'POST'])
def view_post(post_id):
    post = Post.query.filter_by(id=post_id).first()
    comments = Comment.query.filter_by(post_id=post_id).order_by(desc(Comment.date_posted)).all()
    if request.method == 'POST':
        content = request.form['comment']
        comment = Comment(content=content, post_id=post_id, author_id=current_user.id)
        db.session.add(comment)
        db.session.commit()
        return redirect(url_for('community.view_post', post_id=post_id))
    return render_template('post.html', post=post, comments=comments, user=current_user)

@community.route('/create_post', methods=['GET', 'POST'])
@login_required
def create_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, content=form.content.data, author_id=current_user.id)
        db.session.add(post)
        db.session.commit()
        flash('Post created successfully!', 'success')
        return redirect(url_for('community.community_get'))
    else:
        return render_template('create_post.html', form=form)

@community.route('/community/<post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author_id != current_user.id:
        flash('You are not authorized to delete this post', 'error')
        return redirect(url_for('community.view_post', post_id=post_id))
    
    db.session.delete(post)
    db.session.commit() 
    flash('Post deleted successfully', 'success')
    return redirect(url_for('community.community_get'))

@community.route('/community/<post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author_id != current_user.id:
        flash('You are not authorized to edit this post', 'error')
        return redirect(url_for('community.view_post', post_id=post.id))
    if request.method == 'POST':
        post.title = request.form['title']
        post.content = request.form['content']
        db.session.commit()
        flash('Your post has been updated!', 'success')
        return redirect(url_for('community.community_get', post_id=post.id))
    return render_template('edit_post.html', title='Edit Post', post=post)