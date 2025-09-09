import streamlit as st
import pickle
import pandas as pd
import requests
import time
import os


@st.cache_data
def download_similarity_file():
    """Download the similarity.pkl file from Google Drive if it doesn't exist"""

    # Direct download link for your similarity.pkl file
    SIMILARITY_URL = "https://drive.google.com/uc?export=download&id=1JOeVuqgULOdCAu2JmMtMogYlUEiMLZCg"

    if not os.path.exists('similarity.pkl'):
        st.info("📥 Downloading similarity data (this may take a moment)...")

        try:
            response = requests.get(SIMILARITY_URL, stream=True)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            progress_bar = st.progress(0)

            with open('similarity.pkl', 'wb') as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = downloaded / total_size
                            progress_bar.progress(progress)

            progress_bar.empty()
            st.success("✅ Similarity data downloaded successfully!")
            return True

        except Exception as e:
            st.error(f"❌ Failed to download similarity data: {str(e)}")
            st.error("Please check if the Google Drive link is correct and publicly accessible.")
            return False

    return True


def fetch_poster(movie_id):
    try:
        # Add a small delay to prevent rate limiting
        time.sleep(0.1)

        url = f'https://api.themoviedb.org/3/movie/{movie_id}?api_key=8265bd1679663a7ea12ac168da84d2e8&language=en-US'
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if 'poster_path' in data and data['poster_path']:
                return "https://image.tmdb.org/t/p/w500/" + data['poster_path']

        # Return placeholder if no poster found
        return "https://via.placeholder.com/500x750?text=No+Poster"

    except Exception as e:
        # Silently handle the error - don't show warning to user
        print(f"Could not fetch poster for movie ID {movie_id}: {str(e)}")
        return "https://via.placeholder.com/500x750?text=No+Poster"


def recommend(movie):
    try:
        movie_index = movies[movies['title'] == movie].index[0]
        distances = similarity[movie_index]
        movies_list = sorted(list(enumerate(distances)), reverse=True, key=lambda x: x[1])[1:6]

        recommended_movies = []
        recommended_movies_posters = []
        failed_posters = 0

        for i in movies_list:
            movie_id = movies.iloc[i[0]].movie_id
            movie_title = movies.iloc[i[0]].title

            recommended_movies.append(movie_title)

            # Fetch poster with error handling
            poster_url = fetch_poster(movie_id)
            if "placeholder" in poster_url:
                failed_posters += 1
            recommended_movies_posters.append(poster_url)

        # Show summary if some posters failed
        if failed_posters > 0:
            st.info(f"ℹ️ {failed_posters} out of 5 movie posters could not be loaded (using placeholders)")

        return recommended_movies, recommended_movies_posters

    except Exception as e:
        st.error(f"Error getting recommendations: {str(e)}")
        return [], []


# Page config
st.set_page_config(
    page_title="Movie Recommender System",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 Movie Recommender System")
st.write("Select a movie and get personalized recommendations with posters!")

# Download similarity file if needed
if not download_similarity_file():
    st.stop()

# Load Data
try:
    # Load movies (should be small enough for GitHub)
    movies_dict = pickle.load(open('movies.pkl', 'rb'))
    movies = pd.DataFrame(movies_dict)

    # Load similarity matrix (downloaded from Google Drive)
    with st.spinner("Loading similarity data..."):
        similarity = pickle.load(open('similarity.pkl', 'rb'))

except FileNotFoundError as e:
    st.error(f"❌ Required files not found: {str(e)}")
    st.error("Please make sure movies.pkl is uploaded to the repository.")
    st.stop()
except Exception as e:
    st.error(f"❌ Error loading data: {str(e)}")
    st.stop()

selected_movie_name = st.selectbox(
    "Please Select a Movie:",
    movies['title'].values
)

# Recommendation Button
if st.button('🎯 Get Recommendations'):
    with st.spinner('Finding similar movies and fetching posters...'):
        names, posters = recommend(selected_movie_name)

    if names and posters and len(names) == 5:
        st.success(f"Movies similar to '{selected_movie_name}':")

        # Use st.columns instead of st.beta_columns
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.text(names[0])
            st.image(posters[0])

        with col2:
            st.text(names[1])
            st.image(posters[1])

        with col3:
            st.text(names[2])
            st.image(posters[2])

        with col4:
            st.text(names[3])
            st.image(posters[3])

        with col5:
            st.text(names[4])
            st.image(posters[4])

    elif names and posters:
        st.warning(f"Found {len(names)} recommendations instead of 5")
        for i, (name, poster) in enumerate(zip(names, posters)):
            st.write(f"**{i + 1}. {name}**")
            st.image(poster, width=200)
    else:
        st.error("❌ Could not get recommendations. Please try again.")

# Footer
st.markdown("---")
st.markdown("Built with ❤️ using Streamlit and TMDB API")