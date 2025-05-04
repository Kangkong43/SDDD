from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from database import (
    get_user_by_email, create_user, verify_user, get_user_by_id, update_user,
    add_schedule_to_db, remove_schedule_to_db, get_schedules_for_professor,
    update_schedule_in_db, get_all_professors, insert_appointment,
    get_appointments_for_student, get_professor_appointments,
    update_appointment_status, get_user_notifications, create_notification,
    get_appointment_by_id, clear_all_notifications_db, cancel_appointment_in_db,
    check_if_slot_taken, 
    user_has_appointment_at_time 
)
import re
from email_utils import send_status_email
import traceback
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key' 

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'facultime.noreply@gmail.com'    
app.config['MAIL_PASSWORD'] = 'jmod ckqd rywy jtvq'   

# Upload folder for profile pictures
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

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
    print("Appointments:", appointments)
    for appointment in appointments:
        appointment_time_24 = appointment['appointment_time']

        try:
            time_obj = datetime.strptime(appointment_time_24, '%H:%M')
            appointment['formatted_time'] = time_obj.strftime('%I:%M %p')
        except ValueError:
            appointment['formatted_time'] = appointment_time_24 
 

   
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

@app.route('/cancel_appointment/<int:appointment_id>', methods=['POST'])
def cancel_appointment(appointment_id):
    print(f"Received cancellation request for appointment ID: {appointment_id}") 
    if 'user_id' not in session:
        print("User not logged in.") 
        return jsonify({'success': False, 'message': 'Please log in first.'}), 401 

    student_id = session['user_id']
    print(f"Logged in student ID: {student_id}") 
    try:
        print(f"Calling cancel_appointment_in_db for appointment ID {appointment_id} and student ID {student_id}") 
        success = cancel_appointment_in_db(appointment_id, student_id)
        print(f"cancel_appointment_in_db returned: {success}") 

        if success:
            print("Appointment cancelled successfully in DB.") 
            return jsonify({'success': True, 'message': 'Appointment cancelled successfully!'}), 200

        else:
            print("cancel_appointment_in_db returned False.") 
            return jsonify({'success': False, 'message': 'Failed to cancel appointment. It may not exist, belong to you, or its status is not Pending.'}), 400 

    except Exception as e:
      
        print(f"Error cancelling appointment (backend): {str(e)}") 
        return jsonify({'success': False, 'message': 'An internal error occurred while trying to cancel the appointment.'}), 500 


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

@app.route('/book_appointment', methods=['POST'])
def book_appointment():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Please log in first.'}), 401

    user_id = session['user_id']
    appointment_date = request.form.get('appointment_day')
    appointment_time = request.form.get('appointment_time')
    purpose = request.form.get('purpose')
    professor_id = request.form.get('professor_id')
    office = request.form.get('office')
    status = "Pending" # New appointments start as Pending

    # Basic Validation
    if not all([appointment_date, appointment_time, purpose, professor_id, office]):
        return jsonify({'status': 'error', 'message': 'All fields are required!'}), 400

    try:
        # Check 1: Does the *current user* already have *any* active appointment at this exact date and time?
        user_already_booked_at_time = user_has_appointment_at_time(user_id, appointment_date, appointment_time)

        if user_already_booked_at_time:
             print(f"User {user_id} already has an appointment at {appointment_date} {appointment_time}")
             return jsonify({'status': 'error', 'message': 'You already have another appointment scheduled at this exact time. Please choose a different time.'}), 409

        # Check 2: Is this specific time slot already taken by an APPROVED appointment for this professor?
        is_slot_taken = check_if_slot_taken(professor_id, appointment_date, appointment_time)

        if is_slot_taken:
            print(f"Slot {appointment_date} {appointment_time} for professor {professor_id} is already taken.")
            return jsonify({'status': 'error', 'message': 'This time slot is already booked. Please choose another time.'}), 409

        # Check 3: Is the selected time within the professor's available schedule?
        day_of_week_from_form = request.form.get('appointment_day')

        professor_schedules = get_schedules_for_professor(professor_id)
        if not professor_schedules:
            return jsonify({'status': 'error', 'message': 'This professor has no available schedule.'}), 404

        valid_slot_in_schedule = False
        try:
            appt_time_obj = datetime.strptime(appointment_time, "%H:%M").time()

            for sched in professor_schedules:
                 # Use .get() with default None for safety
                 sched_start_time_str = sched.get('start_time')
                 sched_end_time_str = sched.get('end_time')
                 sched_day = sched.get('day')

                 if sched_start_time_str and sched_end_time_str and sched_day:
                     sched_start_time_obj = datetime.strptime(sched_start_time_str, "%H:%M").time()
                     sched_end_time_obj = datetime.strptime(sched_end_time_str, "%H:%M").time()

                     if sched_day == day_of_week_from_form and \
                        sched_start_time_obj <= appt_time_obj <= sched_end_time_obj:
                         valid_slot_in_schedule = True
                         break

        except (ValueError, TypeError) as e:
             print(f"Error parsing time or schedule data: {e}")
             traceback.print_exc()
             return jsonify({'status': 'error', 'message': 'Error validating time slot against professor schedule.'}), 500


        if not valid_slot_in_schedule:
            print(f"Selected time {appointment_time} on {day_of_week_from_form} is not within professor {professor_id}'s schedule.")
            return jsonify({'status': 'error', 'message': 'Selected time is not within professor\'s available time slots.'}), 400


        # If all checks pass, proceed to create the appointment
        print(f"All checks passed. Inserting appointment for user {user_id} with professor {professor_id} on {appointment_date} at {appointment_time}")
        appointment_id = insert_appointment(user_id, professor_id, appointment_date,
                                             appointment_time, purpose, status, office)

        if not appointment_id:
            print("Database insert_appointment failed.")
            return jsonify({'status': 'error', 'message': 'Failed to create appointment.'}), 500

        # --- Send Notification to Professor ---
        print("Appointment created successfully. Attempting to send notifications to professor.")
        student = get_user_by_id(user_id)
        student_name = student.get('name', 'Unknown Student') if student else 'Unknown Student'

        notification_title = "New Appointment Request"
        notification_message = f"Student {student_name} requested an appointment on {appointment_date} at {appointment_time} for '{purpose}'."

        notification_status_msg = [] # Initialize list for status messages

        # --- Send In-App Notification ---
        try:
            notification_created = create_notification(professor_id, notification_title, notification_message, 'appointment_request', appointment_id)
            if notification_created:
                print("In-app notification created successfully for professor.")
                notification_status_msg.append("In-app notification sent to professor.")
            else:
                print("Warning: Failed to create in-app notification for professor.")
                notification_status_msg.append("In-app notification to professor failed.")
        except Exception as notif_e:
            print(f"Error creating in-app notification: {notif_e}")
            traceback.print_exc()
            notification_status_msg.append(f"Error creating in-app notification: {str(notif_e)}")


        # --- Send Email Notification to Professor ---
        professor_details = get_user_by_id(professor_id)
        professor_email = professor_details.get('email') if professor_details else None

        if professor_email:
            try:
                print(f"Attempting to send email to professor {professor_email}...")
                email_sent_success = send_status_email(professor_email, notification_title, notification_message)
                if email_sent_success:
                    print(f"Email notification sent successfully to {professor_email}")
                    notification_status_msg.append("Email notification sent to professor.")
                else:
                    print(f"Failed to send email notification to {professor_email}")
                    notification_status_msg.append("Email notification to professor failed.")
            except Exception as email_e:
                 print(f"Error sending email notification: {email_e}")
                 traceback.print_exc()
                 notification_status_msg.append(f"Error sending email notification: {str(email_e)}")
        else:
            print(f"Skipped sending email: No email address found for professor ID {professor_id}")
            notification_status_msg.append("Email notification skipped (professor email missing).")


        # Booking successful, return success response with notification status
        final_message = f'Appointment booked successfully! It is now pending approval. {" ".join(notification_status_msg)}'
        print(f"Returning success response: {final_message}")
        return jsonify({'status': 'success', 'message': final_message}), 201 # Created

    except Exception as e:
        # Catch any unexpected errors during the process before notifications
        print(f"An unexpected error occurred during booking: {str(e)}")
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': f'An internal server error occurred: {str(e)}'}), 500

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
            appointment['formatted_time'] = appointment_time_24  
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

@app.route('/update_status/<int:appointment_id>', methods=['POST'])
def update_status(appointment_id):
    if 'user_id' not in session:
        return jsonify(success=False, message="Unauthorized"), 401

    professor_id = session['user_id'] 
    data = request.get_json()

    new_status = data.get('status')
    reason = data.get('reason') 

    print(f"Received status: {new_status}, reason: {reason}") 
   
    if not appointment_id or not new_status:
        return jsonify(success=False, message="Missing appointment ID or status"), 400

    allowed_statuses = ['Approved', 'Rejected', 'Completed', 'Cancelled']
    if new_status not in allowed_statuses:
        return jsonify(success=False, message="Invalid status provided."), 400

    if new_status in ['Rejected', 'Cancelled'] and not reason:
         return jsonify(success=False, message=f"Reason is required for status: {new_status}."), 400

    try:
        print("Attempting to update appointment status in database...")
        success, student_id = update_appointment_status(appointment_id, new_status, professor_id, reason)

        message_body = ""
        notification_title = "Appointment Status Update"
        email_sent_success = False
        notification_created = False
        notification_status_msg = [] 

        if success and student_id:
          
            print("Successfully updated appointment status, attempting to send notifications...")

            try:
                appointment = get_appointment_by_id(appointment_id)

                if appointment:
                   
                    student_details = get_user_by_id(student_id)
                    if student_details:
                        student_name = student_details.get('name', 'Student')
                        student_email = student_details.get('email') 
                        professor_details = get_user_by_id(professor_id)
                        professor_name = professor_details.get('name', 'The professor')

                        message_body = f"Dear {student_name},\n\nYour appointment scheduled for {appointment.get('appointment_date', 'a certain date')} at {appointment.get('appointment_time', 'a certain time')} has been {new_status.lower()} by {professor_name}."

                     
                        stored_reason = appointment.get('reason')
                        if new_status in ['Rejected', 'Cancelled'] and stored_reason:
                            message_body += f"\nReason: {stored_reason}"

                        message_body += "\n\nPlease check your dashboard for details." 

                        notification_type = 'appointment_status' 
                        print("Attempting to create in-app notification...")
                        notification_created = create_notification(student_id, notification_title, message_body, notification_type, appointment_id)
                        if notification_created:
                             print("In-app notification created successfully.")
                             notification_status_msg.append("In-app notification sent.")
                        else:
                             print("Warning: Failed to create in-app notification.")
                             notification_status_msg.append("In-app notification failed.")


                      
                        if student_email: 
                             print(f"Attempting to send email to {student_email}...")
                             email_sent_success = send_status_email(student_email, notification_title, message_body)
                             if email_sent_success:
                                  print(f"Email notification sent to {student_email}")
                                  notification_status_msg.append("Email notification sent.")
                             else:
                                  print(f"Failed to send email notification to {student_email}")
                                  notification_status_msg.append("Email notification failed.")
                        else:
                             print(f"Skipped sending email: No email address found for student ID {student_id}")
                             notification_status_msg.append("Email notification skipped (no email address).")

                    else:
                        print("Could not retrieve student details for notification.")
                        notification_status_msg.append("Notification failed (student details missing).")
                else:
                    print("Could not retrieve appointment details after update for notification.")
                    notification_status_msg.append("Notification failed (appointment details missing).")

            except Exception as notification_error:
               
                 print(f"An error occurred during notification/email sending: {str(notification_error)}")
                 traceback.print_exc()
                 notification_status_msg.append(f"Notification process encountered an error: {str(notification_error)}")

            final_message = f'Appointment status updated to {new_status}! {" ".join(notification_status_msg)}'
            print(f"Returning success response: {final_message}")
            return jsonify(success=True, message=final_message), 200

        elif not success:
  
            print("Internal update_appointment_status failed.")

            return jsonify(success=False, message="Failed to update appointment status (check if the appointment exists and belongs to this professor)"), 400 

        else:
         
            print("An unexpected issue occurred after updating status (success is True but student_id is None?).")

            return jsonify(success=False, message="An unexpected error occurred."), 500 


    except Exception as e:
   
        print(f"An unexpected error occurred in update_status route: {str(e)}")

        traceback.print_exc()
        return jsonify(success=False, message=f"An internal server error occurred: {str(e)}"), 500

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
            user = get_user_by_id(session['user_id']) 
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
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized - Please log in'}), 401
    prof_id = session['user_id']

    
    try:
        schedules = get_schedules_for_professor(prof_id)
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
    
    new_status = 'Approved' if action == 'approved' else 'Rejected'
    success = update_appointment_status(appointment_id, new_status)
    
    if success:
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
