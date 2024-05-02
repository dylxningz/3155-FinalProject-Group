from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import login_required, current_user
from app import db
from app.models import Post, Comment, User, PostLike
from app.forms import PostForm
from sqlalchemy import desc
from app.spotify_utils import get_song_details



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
    if not post:
 
        abort(404, description=f"There is no post with ID { post_id }.")

    comments = Comment.query.filter_by(post_id=post_id).order_by(desc(Comment.date_posted)).all()
    song_details = None
    if post.spotify_song_id:
        song_details = get_song_details(post.spotify_song_id) 

    if request.method == 'POST':
        content = request.form['comment']
        comment = Comment(content=content, post_id=post_id, author_id=current_user.id)
        db.session.add(comment)
        db.session.commit()
        return redirect(url_for('community.view_post', post_id=post_id))
    
    return render_template('post.html', post=post, comments=comments, user=current_user, song_details=song_details)


@community.route('/create_post', methods=['GET', 'POST'])
@login_required
def create_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(
            title=form.title.data,
            content=form.content.data,
            author_id=current_user.id,
            spotify_song_id=form.spotify_song_id.data if form.spotify_song_id.data else None
        )
        db.session.add(post)
        db.session.commit()
        flash('Post created successfully!', 'success')
        return redirect(url_for('community.community_get'))
    else:
        return render_template('create_post.html', form=form)

@community.route('/community/<post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id, description=f"There is no post with ID { post_id }.")
    if post.author_id != current_user.id:
        flash('You are not authorized to delete this post', 'error')
        return redirect(url_for('community.view_post', post_id=post_id))
    
    # Delete likes associated with the post
    likes = PostLike.query.filter_by(post_id=post_id).all()
    for like in likes:
        db.session.delete(like)
    
    # Delete comments associated with the post
    comments = Comment.query.filter_by(post_id=post_id).all()
    for comment in comments:
        db.session.delete(comment)
    
    # Finally, delete the post itself
    db.session.delete(post)
    db.session.commit() 
    
    flash('Post deleted successfully', 'success')
    return redirect(url_for('community.community_get'))

@community.route('/community/<post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = Post.query.get_or_404(post_id, description=f"There is no post with ID { post_id }.")
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


@community.route('/delete_comment/<int:comment_id>', methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id, description=f"There is no comment with ID { comment_id }.")
    if comment.author_id != current_user.id:
        flash('You are not authorized to delete this comment', 'error')
        return redirect(url_for('community.view_post', post_id=comment.post_id))
    
    db.session.delete(comment)
    db.session.commit()
    flash('Comment deleted successfully', 'success')
    return redirect(url_for('community.view_post', post_id=comment.post_id))


@community.route('/edit_comment/<int:comment_id>', methods=['GET', 'POST'])
@login_required
def edit_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id, description=f"There is no comment with ID { comment_id }.")
    if comment.author_id != current_user.id:
        flash('You are not authorized to edit this comment', 'error')
        return redirect(url_for('community.view_post', post_id=comment.post_id))
    
    if request.method == 'POST':
        comment.content = request.form['content']
        db.session.commit()
        flash('Comment updated successfully!', 'success')
        return redirect(url_for('community.view_post', post_id=comment.post_id))
    
    return render_template('edit_comment.html', comment=comment)


@community.route('/toggle_like/<int:post_id>', methods=['POST'])
@login_required
def toggle_like(post_id):
    post = Post.query.get_or_404(post_id)
    like = PostLike.query.filter_by(user_id=current_user.id, post_id=post_id).first()

    if like:
        db.session.delete(like)
        db.session.commit()
        liked = False  
        message = 'You have unliked the post.'
    else:
        like = PostLike(user_id=current_user.id, post_id=post_id)
        db.session.add(like)
        db.session.commit()
        liked = True
        message = 'You liked the post!'

    likes_count = PostLike.query.filter_by(post_id=post_id).count()
    return jsonify({
        'success': True,
        'liked': liked,
        'likes': likes_count,
        'message': message
    })
