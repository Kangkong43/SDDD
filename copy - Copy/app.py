from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from database import get_user_by_email, create_user, verify_user, get_user_by_id, update_user,add_schedule_to_db,remove_schedule_to_db,get_schedules_for_professor,update_schedule_in_db,get_all_professors,insert_appointment,check_duplicate_appointment,get_appointments_for_student,get_professor_appointments,update_appointment_status,get_user_notifications,create_notification,get_appointment_by_id,clear_all_notifications_db
import re

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this in production

# Upload folder for profile pictures
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('student_dashboard'))
    return render_template('index.html')
# Login Logic
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = verify_user(email, password)
        if user:
            session['user_id'] = user['id']

            return redirect(url_for('student_dashboard')) if user['role'] == 'student' else redirect(url_for('professor_dashboard'))
        else:
            flash('Invalid email or password.', 'error')
    return render_template('login.html')

#Register Logic
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        if get_user_by_email(email):
            flash('Email already exists!', 'error')
            return render_template('register.html')
        create_user(name, email, password, role)
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

##------------------------------------------------------------------- STUDENT ------------------------------------------------------------------------##

@app.route('/student_dashboard')
def student_dashboard():
    if 'user_id' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('login'))
    user = get_user_by_id(session['user_id'])
    student_id = session['user_id']
    appointments = get_appointments_for_student(student_id)
   
    appointments = [dict(row) for row in appointments]
    for appointment in appointments:
        appointment_time_24 = appointment['appointment_time']

        try:
           
          
            time_obj = datetime.strptime(appointment_time_24, '%H:%M')
           
          
            appointment['formatted_time'] = time_obj.strftime('%I:%M %p')
           
        except ValueError:
          
            appointment['formatted_time'] = appointment_time_24  # Fallback to the original text format 
 

   
    total_count = len(appointments)
    
    pending_count = len([a for a in appointments if a['status'] == 'Pending'])
    approved_count = len([a for a in appointments if a['status'] == 'Approved'])
    rejected_count = len([a for a in appointments if a['status'] == 'Rejected'])


    return render_template('student_dashboard.html', user=user, 
                         appointments=appointments,
                         total_count=total_count,
                         pending_count=pending_count,
                         approved_count=approved_count,
                         rejected_count=rejected_count) if user else redirect(url_for('login'))
##------------student  account settings------------##

@app.route('/saccount_settings', methods=['GET', 'POST'])
def saccount_settings():
    if 'user_id' not in session:
        return jsonify({'error': 'Please log in first.'}), 401

    user = get_user_by_id(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found.'}), 404

    if request.method == 'POST':
        # Get form data
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm-password', '')
        profile_picture = user.get('profile_picture')

        print(f"User ID: {user['id']}")
        print(f"Name: {name}, Email: {email}, Password: {password}, Confirm Password: {confirm_password}")

        # Validate form data
        if not name or len(name) < 3:
            return jsonify({'error': 'Name must be at least 3 characters'}), 400

        # Simple email validation
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return jsonify({'error': 'Please enter a valid email address'}), 400

        # Check for duplicate email
        existing_user = get_user_by_email(email)
        if existing_user and existing_user['id'] != user['id']:
            return jsonify({'error': 'This email is already in use'}), 409

        # Password validation
        if password:
            if password != confirm_password:
                return jsonify({'error': 'Passwords do not match'}), 400

            if len(password) < 8:
                return jsonify({'error': 'Password must be at least 8 characters'}), 400

            password = generate_password_hash(password)
            print(f"Hashed Password: {password}")
        else:
            password = None

        # Handle profile picture
        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file and file.filename:
                if file.content_length > 2 * 1024 * 1024:  # 2MB limit
                    return jsonify({'error': 'File too large (max 2MB)'}), 413

                if allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    profile_picture = filename
                else:
                    return jsonify({'error': 'Invalid file type'}), 415

        # Update user
        try:
            update_user(user['id'], name, email, password, profile_picture)
            # Refresh user data
            user = get_user_by_id(session['user_id'])
            
           
            return jsonify({'message': 'Profile updated successfully!'}), 200
        except Exception as e:
            app.logger.error(f"Error updating user {user['id']}: {str(e)}")
         
            return jsonify({'error': 'An error occurred while updating your profile'}), 500

    return render_template('saccount_settings.html', user=user)



##------------student book appointment------------##

@app.route('/sbook_appointment')
def sbook_appointment():
    if 'user_id' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('login'))
    user = get_user_by_id(session['user_id'])
    professors = get_all_professors()
    

    return render_template('sbook_appointment.html', user=user,professors=professors)



from datetime import datetime

@app.route('/book_appointment', methods=['POST'])
def book_appointment():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Please log in first.'})

    user_id = session['user_id']
    appointment_date = request.form.get('appointment_day')
    appointment_time = request.form.get('appointment_time')
    purpose = request.form.get('purpose')
    professor_id = request.form.get('professor_id')
    office = request.form.get('office')

    status = "Pending"

    if not all([appointment_date, appointment_time, purpose, professor_id, office]):
        return jsonify({'status': 'error', 'message': 'All fields are required!'})

    try:
        professor_schedules = get_schedules_for_professor(professor_id)
        if not professor_schedules:
            return jsonify({'status': 'error', 'message': 'This professor has no available schedule.'})

        # Get day of week from appointment_date
        day_of_week = request.form.get('appointment_day') 

        # Check if appointment time is within professor's schedule
        appt_time = datetime.strptime(appointment_time, "%H:%M")
        valid_slot = False

        for sched in professor_schedules:
            if sched['day'] == day_of_week:
                start = datetime.strptime(sched['start_time'], "%H:%M")
                end = datetime.strptime(sched['end_time'], "%H:%M")
                if start <= appt_time <= end:
                    valid_slot = True
                    break

        if not valid_slot:
            return jsonify({'status': 'error', 'message': 'Selected time is not within professor\'s available time slots.'})

        if check_duplicate_appointment(professor_id, appointment_date, appointment_time):
            return jsonify({'status': 'error', 'message': 'You already have an appointment at this time.'})

        appointment_id = insert_appointment(user_id, professor_id, appointment_date,
                                            appointment_time, purpose, status, office)
        if not appointment_id:
            return jsonify({'status': 'error', 'message': 'Failed to create appointment.'})

        student = get_user_by_id(user_id)
        student_name = student.get('name', 'Unknown Student') if student else 'Unknown Student'

        title = "New Appointment Request"
        message = f"Student {student_name} requested an appointment on {appointment_date} at {appointment_time}"

        if not create_notification(professor_id, title, message, 'appointment_request', appointment_id):
            return jsonify({'status': 'warning', 'message': 'Appointment booked, but notification failed.'})

        return jsonify({'status': 'success', 'message': 'Appointment booked successfully!'})

    except Exception as e:
        return jsonify({'status': 'error', 'message': f'An error occurred: {str(e)}'})

##------------student notification------------##

@app.route('/snotification')
def snotification():
    if 'user_id' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('login'))
    user = get_user_by_id(session['user_id'])
    notifications = get_user_notifications(user['id'])
    return render_template('snotification.html', user=user,notifications=notifications)

@app.route('/clear_all_notifications', methods=['POST'])
def clear_all_notifications():
    if 'user_id' not in session:
        return jsonify(success=False, message="Unauthorized")
    
    success = clear_all_notifications_db(session['user_id'])
    return jsonify(success=success)
##------------student logout------------##


@app.route('/slogout')
def slogout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))


##------------------------------------------------------------------- PROFESSOR ------------------------------------------------------------------------##

@app.route('/professor_dashboard')
def professor_dashboard():
    if 'user_id' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('login'))
    user = get_user_by_id(session['user_id'])
    professor_id = session['user_id']
    appointments = get_professor_appointments(professor_id)
    for appointment in appointments:
        appointment_time_24 = appointment['appointment_time']
     
  
        try:
         
          
            time_obj = datetime.strptime(appointment_time_24, '%H:%M')
   
       
            appointment['formatted_time'] = time_obj.strftime('%I:%M %p')
            
        except ValueError:
            # Handle cases where the time format is invalid (in case of bad data)
            appointment['formatted_time'] = appointment_time_24  # Fallback to the original text format 
    pending_count = len([a for a in appointments if a['status'] == 'Pending'])
    approved_count = len([a for a in appointments if a['status'] == 'Approved'])
    completed_count = len([a for a in appointments if a['status'] == 'Completed'])
    rejected_count = len([a for a in appointments if a['status'] == 'Rejected'])

    return render_template('professor_dashboard.html', user=user, 
                        appointments=appointments,
                        pending_count=pending_count,
                        approved_count=approved_count,
                        completed_count=completed_count,
                        rejected_count=rejected_count)
##
@app.route('/update_status/<int:appointment_id>', methods=['POST'])

def update_status(appointment_id):
  
    if 'user_id' not in session:
        return jsonify(success=False, message="Unauthorized")

    professor_id = session['user_id']  # The logged-in user is the professor
    data = request.get_json()
  
    new_status = data.get('status')

    if not appointment_id or not new_status:
        return jsonify(success=False, message="Missing appointment ID or status")

    try:
        # Update the appointment status in the database and get the student ID
        success, student_id = update_appointment_status(appointment_id, new_status, professor_id)
        if success and student_id:
            # After updating the status, send a notification to the student
            appointment = get_appointment_by_id(appointment_id)
            
            if appointment:
                student_details = get_user_by_id(student_id)
                if student_details:
                    student_name = student_details['name']
                    professor_details = get_user_by_id(professor_id)
                    professor_name = professor_details.get('name', 'The professor') # Get professor's name

                    # Create the notification message
                    message = f"Dear {student_name}, your appointment scheduled for {appointment['appointment_date']} at {appointment['appointment_time']} has been {new_status.lower()} by {professor_name}."
                    notification_type = 'appointment_status'
                    # Create the notification
                    notification_created = create_notification(student_id, "Appointment Status Update", message, notification_type)

                    if notification_created:
                        return jsonify(success=True)
                    else:
                        return jsonify(success=False, message="Failed to create notification")
                else:
                    return jsonify(success=False, message="Could not retrieve student details")
            else:
                return jsonify(success=False, message="Could not retrieve appointment details")

        elif not success:
            return jsonify(success=False, message="Failed to update appointment status (check if the appointment exists and belongs to this professor)")
        else:
            return jsonify(success=False, message="Failed to retrieve student ID after updating status")

    except Exception as e:
        return jsonify(success=False, message=f"An error occurred: {str(e)}")
##------------professor  account settings------------##

@app.route('/paccountSettings', methods=['GET', 'POST'])
def paccountSettings():
    if 'user_id' not in session:
        return jsonify({'error': 'Please log in first.'}), 401

    user = get_user_by_id(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found.'}), 404

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm-password', '')
        profile_picture = user.get('profile_picture')

        # Validation
        if not name or len(name) < 3:
            return jsonify({'error': 'Name must be at least 3 characters'}), 400

        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return jsonify({'error': 'Please enter a valid email address'}), 400

        existing_user = get_user_by_email(email)
        if existing_user and existing_user['id'] != user['id']:
            return jsonify({'error': 'This email is already in use'}), 409

        if password:
            if password != confirm_password:
                return jsonify({'error': 'Passwords do not match'}), 400

            if len(password) < 8:
                return jsonify({'error': 'Password must be at least 8 characters'}), 400

            password = generate_password_hash(password)
        else:
            password = None

        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                profile_picture = filename
            else:
                return jsonify({'error': 'Invalid file type'}), 415

        try:
            update_user(user['id'], name, email, password, profile_picture)
            user = get_user_by_id(session['user_id']) #refresh user data
            return jsonify({'message': 'Profile updated successfully!'}), 200
        except Exception as e:
            app.logger.error(f"Error updating user {user['id']}: {str(e)}")
            return jsonify({'error': 'An error occurred while updating your profile'}), 500

    return render_template('paccountSettings.html', user=user)

##------------professor add sched------------##

@app.route('/pbookAppointment')
def pbookAppointment():
    if 'user_id' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('login'))
    user = get_user_by_id(session['user_id'])
    schedules = get_schedules_for_professor(session['user_id'])
    return render_template('pbookAppointment.html', user=user, schedules=schedules)

@app.route('/clear_schedules', methods=['POST'])
def clear_schedules():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    from database import clear_schedules_for_professor
    result = clear_schedules_for_professor(session['user_id'])

    if result == 'success':
        return '', 204
    else:
        return jsonify({'error': 'Failed to clear schedules'}), 500


@app.route('/add_schedule', methods=['POST'])
def add_schedule():
    data = request.get_json()
    day = data.get('day')
    office = data.get('office')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    prof_id = session.get('user_id')

    if not all([day, office,prof_id,start_time, end_time]):
        return jsonify({'error': 'Missing fields'}), 400

    result = add_schedule_to_db(prof_id, day, office, start_time, end_time)

    if result == 'success':
        return jsonify({'success': True})
    elif result == 'exists':
        return jsonify({'error': 'Schedule already exists.'}), 409
    else:
        return jsonify({'error': 'Failed to add schedule.'}), 500
    


@app.route('/remove_schedule', methods=['POST'])
def remove_schedule():
    data = request.get_json()
    day = data.get('day')
    office = data.get('office')
    start_time = data.get('start_time')
    end_time = data.get('end_time')

    prof_id = session.get('user_id')

    if not all([day, office, start_time, end_time, prof_id]):

        return jsonify({'error': 'Missing fields'}), 400

    result = remove_schedule_to_db(prof_id, day, office, start_time, end_time)

    if result == 'success':
        return jsonify({'success': True})
    elif result == 'no_schedule_found':
        return jsonify({'error': 'No schedule found to remove.'}), 404
    else:
        return jsonify({'error': 'Failed to remove schedule.'}), 500

@app.route('/get_schedules', methods=['GET'])
def get_schedules():
    # Validate session first
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized - Please log in'}), 401

    # Get professor ID from session (more secure than URL parameter)
    prof_id = session['user_id']

    
    try:
        schedules = get_schedules_for_professor(prof_id)
     
        # Convert schedules to proper JSON format
        formatted_schedules = []
        for sched in schedules:
            formatted_schedules.append({
                'day': sched.day,
                'office': sched.office,
                'start_time': sched.start_time.strftime('%H:%M') if sched.start_time else '',
                'end_time': sched.end_time.strftime('%H:%M') if sched.end_time else ''
            })
        
        return jsonify({
            'success': True,
            'schedules': formatted_schedules
        })
        
    except Exception as e:
        app.logger.error(f"Error fetching schedules: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'Could not retrieve schedules'
        }), 500

@app.route('/get_schedule/<int:prof_id>', methods=['GET'])
def get_schedule_for_student(prof_id):
    try:
        schedules = get_schedules_for_professor(prof_id)
        return jsonify({
            'success': True,
            'schedules': schedules
        })
    except Exception as e:
        app.logger.error(f"Error fetching student view schedules: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


##------------professor notification------------##

@app.route('/pnotification')
def pnotification():
    if 'user_id' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('login'))
    user = get_user_by_id(session['user_id'])
    notifications = get_user_notifications(user['id'])
    return render_template('pnotification.html', user=user, notifications=notifications)

@app.route('/respond_to_appointment', methods=['POST'])
def respond_to_appointment():
    if 'user_id' not in session:
        return jsonify(success=False, message="Unauthorized")
    
    data = request.get_json()
    appointment_id = data['appointment_id']
    action = data['action']
    
    # Update appointment status
    new_status = 'Approved' if action == 'approved' else 'Rejected'
    success = update_appointment_status(appointment_id, new_status)
    
    if success:
        # Mark notification as read or create a new one
        return jsonify(success=True)
    else:
        return jsonify(success=False, message="Failed to update appointment")

##------------professor logout------------##


@app.route('/plogout')
def plogout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))



if __name__ == '__main__':
    app.run(debug=True)
