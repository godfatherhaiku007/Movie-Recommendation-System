import streamlit as st
import pickle
import pandas as pd
import requests
import time
import os


def download_large_file_from_google_drive(file_id, destination):
    """Download a large file from Google Drive"""

    def get_confirm_token(response):
        for key, value in response.cookies.items():
            if key.startswith('download_warning'):
                return value
        return None

    def save_response_content(response, destination, chunk_size=32768):
        total_size = int(response.headers.get('content-length', 0))
        progress_bar = st.progress(0)

        with open(destination, "wb") as f:
            downloaded = 0
            for chunk in response.iter_content(chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        progress = downloaded / total_size
                        progress_bar.progress(progress)
        progress_bar.empty()

    URL = "https://docs.google.com/uc?export=download"
    session = requests.Session()

    response = session.get(URL, params={'id': file_id}, stream=True)
    token = get_confirm_token(response)

    if token:
        params = {'id': file_id, 'confirm': token}
        response = session.get(URL, params=params, stream=True)

    save_response_content(response, destination)


@st.cache_data
def load_similarity_data():
    """Load similarity data, downloading from Google Drive if necessary"""

    file_id = "1JOeVuqgULOdCAu2JmMtMogYlUEiMLZCg"

    if not os.path.exists('similarity.pkl'):
        st.info("📥 Downloading similarity data from Google Drive (this may take a moment)...")

        try:
            download_large_file_from_google_drive(file_id, 'similarity.pkl')

            # Verify the file was downloaded correctly
            try:
                with open('similarity.pkl', 'rb') as f:
                    test_load = pickle.load(f)
                st.success("✅ Similarity data downloaded and verified successfully!")
            except Exception as verify_error:
                st.error(f"❌ Downloaded file is corrupted: {str(verify_error)}")
                if os.path.exists('similarity.pkl'):
                    os.remove('similarity.pkl')
                return None

        except Exception as e:
            st.error(f"❌ Failed to download similarity data: {str(e)}")
            st.error("Please try refreshing the page or contact support.")
            return None

    # Load the similarity matrix
    try:
        with open('similarity.pkl', 'rb') as f:
            similarity = pickle.load(f)
        return similarity
    except Exception as e:
        st.error(f"❌ Error loading similarity data: {str(e)}")
        if os.path.exists('similarity.pkl'):
            os.remove('similarity.pkl')
        return None


def fetch_poster(movie_id):
    try:
        time.sleep(0.1)
        url = f'https://api.themoviedb.org/3/movie/{movie_id}?api_key=8265bd1679663a7ea12ac168da84d2e8&language=en-US'
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if 'poster_path' in data and data['poster_path']:
                return "https://image.tmdb.org/t/p/w500/" + data['poster_path']

        return "https://via.placeholder.com/500x750?text=No+Poster"

    except Exception as e:
        print(f"Could not fetch poster for movie ID {movie_id}: {str(e)}")
        return "https://via.placeholder.com/500x750?text=No+Poster"


def recommend(movie, movies, similarity):
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

            poster_url = fetch_poster(movie_id)
            if "placeholder" in poster_url:
                failed_posters += 1
            recommended_movies_posters.append(poster_url)

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

# Load movies data (should be in the repository)
try:
    movies_dict = pickle.load(open('movies.pkl', 'rb'))
    movies = pd.DataFrame(movies_dict)
except FileNotFoundError:
    st.error("❌ movies.pkl not found. Please make sure it's uploaded to your repository.")
    st.stop()
except Exception as e:
    st.error(f"❌ Error loading movies data: {str(e)}")
    st.stop()

# Load similarity data (download from Google Drive if needed)
with st.spinner("Loading similarity data..."):
    similarity = load_similarity_data()

if similarity is None:
    st.error("❌ Could not load similarity data. Please try refreshing the page.")
    st.stop()

# Main app interface
selected_movie_name = st.selectbox(
    "Please Select a Movie:",
    movies['title'].values
)

if st.button('🎯 Get Recommendations'):
    with st.spinner('Finding similar movies and fetching posters...'):
        names, posters = recommend(selected_movie_name, movies, similarity)

    if names and posters and len(names) == 5:
        st.success(f"Movies similar to '{selected_movie_name}':")

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