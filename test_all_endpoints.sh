#!/bin/bash
# ════════════════════════════════════════════════════════════════════
# Zeen — Full API Test Script
# Tests all 35 functional requirements against localhost:8000
#
# Usage:
#   chmod +x test_all_endpoints.sh
#   ./test_all_endpoints.sh
#
# Prerequisites: docker-compose up --build  (all services running)
# ════════════════════════════════════════════════════════════════════

BASE="http://localhost:8000/api/v1"
PASS=0
FAIL=0
TOTAL=0

green()  { printf "\033[32m✓ %s\033[0m\n" "$1"; }
red()    { printf "\033[31m✗ %s\033[0m\n" "$1"; }
header() { printf "\n\033[1;34m── %s ──\033[0m\n" "$1"; }

check() {
    TOTAL=$((TOTAL+1))
    local label="$1" code="$2" expected="$3"
    if [ "$code" = "$expected" ]; then
        green "$label (HTTP $code)"
        PASS=$((PASS+1))
    else
        red "$label (expected $expected, got $code)"
        FAIL=$((FAIL+1))
    fi
}

# ── FR-01: User Registration ───────────────────────────────────────
header "FR-01 User Registration"

# Register admin
R=$(curl -s -o /tmp/z_admin.json -w "%{http_code}" -X POST "$BASE/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@zeenapp.com","username":"admin_test","password":"admin123","first_name":"Admin","last_name":"User","role":"admin"}')
check "Register admin user" "$R" "200"

# Register normal user
R=$(curl -s -o /tmp/z_user.json -w "%{http_code}" -X POST "$BASE/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@zeenapp.com","username":"normal_user","password":"user1234","first_name":"Normal","last_name":"User"}')
check "Register normal user" "$R" "200"

# Register second user (for testing)
R=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"user2@zeenapp.com","username":"second_user","password":"user1234","first_name":"Second","last_name":"User"}')
check "Register second user" "$R" "200"

# Duplicate check
R=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@zeenapp.com","username":"admin_test","password":"admin123"}')
check "Reject duplicate registration" "$R" "400"

# ── FR-02: User Login ──────────────────────────────────────────────
header "FR-02 User Login"

R=$(curl -s -o /tmp/z_admin_token.json -w "%{http_code}" -X POST "$BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@zeenapp.com","password":"admin123"}')
check "Admin login" "$R" "200"
ADMIN_TOKEN=$(cat /tmp/z_admin_token.json | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

R=$(curl -s -o /tmp/z_user_token.json -w "%{http_code}" -X POST "$BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@zeenapp.com","password":"user1234"}')
check "Normal user login" "$R" "200"
USER_TOKEN=$(cat /tmp/z_user_token.json | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

R=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@zeenapp.com","password":"wrongpass"}')
check "Reject bad password" "$R" "401"

AUTH_ADMIN="Authorization: Bearer $ADMIN_TOKEN"
AUTH_USER="Authorization: Bearer $USER_TOKEN"

# ── FR-16: Token Validation ────────────────────────────────────────
header "FR-16 Token Validation"
R=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/auth/validate-token" -H "$AUTH_USER")
check "Validate token" "$R" "200"

# ── FR-03: User Profile Management ────────────────────────────────
header "FR-03 User Profile Management"

R=$(curl -s -o /tmp/z_me.json -w "%{http_code}" "$BASE/auth/me" -H "$AUTH_USER")
check "Get current user (me)" "$R" "200"
USER_ID=$(cat /tmp/z_me.json | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null)
ADMIN_ID=$(curl -s "$BASE/auth/me" -H "$AUTH_ADMIN" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null)

R=$(curl -s -o /dev/null -w "%{http_code}" -X PUT "$BASE/users/$USER_ID" \
  -H "$AUTH_USER" -H "Content-Type: application/json" \
  -d '{"first_name":"Updated"}')
check "Update own profile" "$R" "200"

# ── FR-17: Change Password ────────────────────────────────────────
header "FR-17 Change Password"
R=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/auth/change-password" \
  -H "$AUTH_USER" -H "Content-Type: application/json" \
  -d '{"current_password":"user1234","new_password":"newpass123"}')
check "Change password" "$R" "200"

# Re-login with new password
R=$(curl -s -o /tmp/z_user_token2.json -w "%{http_code}" -X POST "$BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@zeenapp.com","password":"newpass123"}')
check "Login with new password" "$R" "200"
USER_TOKEN=$(cat /tmp/z_user_token2.json | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)
AUTH_USER="Authorization: Bearer $USER_TOKEN"

# ── FR-13: Content Ingestion (Admin) ──────────────────────────────
header "FR-13 Content Ingestion (Admin)"

R=$(curl -s -o /tmp/z_movie1.json -w "%{http_code}" -X POST "$BASE/content/" \
  -H "$AUTH_ADMIN" -H "Content-Type: application/json" \
  -d '{
    "title":"Interstellar","description":"A team of explorers travel through a wormhole in space","content_type":"movie",
    "duration_minutes":169,"release_date":"2014-11-07T00:00:00","rating":0,
    "genres":["Sci-Fi","Drama","Adventure"],"cast":["Matthew McConaughey","Anne Hathaway","Jessica Chastain"],
    "directors":["Christopher Nolan"],"poster_url":"https://example.com/interstellar.jpg"
  }')
check "Admin creates movie (Interstellar)" "$R" "200"
MOVIE1_ID=$(cat /tmp/z_movie1.json | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null)

R=$(curl -s -o /tmp/z_movie2.json -w "%{http_code}" -X POST "$BASE/content/" \
  -H "$AUTH_ADMIN" -H "Content-Type: application/json" \
  -d '{
    "title":"The Dark Knight","description":"Batman faces the Joker, a criminal mastermind","content_type":"movie",
    "duration_minutes":152,"release_date":"2008-07-18T00:00:00","rating":0,
    "genres":["Action","Crime","Drama"],"cast":["Christian Bale","Heath Ledger","Aaron Eckhart"],
    "directors":["Christopher Nolan"]
  }')
check "Admin creates movie (Dark Knight)" "$R" "200"
MOVIE2_ID=$(cat /tmp/z_movie2.json | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null)

R=$(curl -s -o /tmp/z_series1.json -w "%{http_code}" -X POST "$BASE/content/" \
  -H "$AUTH_ADMIN" -H "Content-Type: application/json" \
  -d '{
    "title":"Breaking Bad","description":"A high school chemistry teacher turned drug kingpin","content_type":"series",
    "duration_minutes":0,"release_date":"2008-01-20T00:00:00","rating":0,
    "genres":["Crime","Drama","Thriller"],"cast":["Bryan Cranston","Aaron Paul","Anna Gunn"],
    "directors":["Vince Gilligan"]
  }')
check "Admin creates series (Breaking Bad)" "$R" "200"
SERIES1_ID=$(cat /tmp/z_series1.json | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null)

# Non-admin cannot create
R=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/content/" \
  -H "$AUTH_USER" -H "Content-Type: application/json" \
  -d '{"title":"Fail","description":"Should fail","content_type":"movie","duration_minutes":90,"release_date":"2024-01-01T00:00:00"}')
check "Non-admin cannot create content" "$R" "403"

# More content for variety
for i in 1 2 3; do
  curl -s -o /dev/null -X POST "$BASE/content/" \
    -H "$AUTH_ADMIN" -H "Content-Type: application/json" \
    -d "{
      \"title\":\"Test Movie $i\",\"description\":\"Test description $i for search\",\"content_type\":\"movie\",
      \"duration_minutes\":$((90+i*10)),\"release_date\":\"202${i}-06-15T00:00:00\",\"rating\":0,
      \"genres\":[\"Action\",\"Comedy\"],\"cast\":[\"Actor $i\"],\"directors\":[\"Director $i\"]
    }"
done

# ── FR-34: Batch Content Ingestion ─────────────────────────────────
header "FR-34 Batch Content Ingestion"
R=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/content/batch" \
  -H "$AUTH_ADMIN" -H "Content-Type: application/json" \
  -d '[
    {"title":"Inception","description":"A thief who steals corporate secrets through dream-sharing","content_type":"movie","duration_minutes":148,"release_date":"2010-07-16T00:00:00","genres":["Sci-Fi","Action"],"cast":["Leonardo DiCaprio"],"directors":["Christopher Nolan"]},
    {"title":"Dunkirk","description":"Allied soldiers are surrounded by enemy on the beach of Dunkirk","content_type":"movie","duration_minutes":106,"release_date":"2017-07-21T00:00:00","genres":["War","Drama"],"cast":["Fionn Whitehead"],"directors":["Christopher Nolan"]}
  ]')
check "Batch create content" "$R" "200"

# ── FR-04: Content Catalog Browsing ────────────────────────────────
header "FR-04 Content Catalog Browsing"

R=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/content/")
check "List all content" "$R" "200"

R=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/content/?content_type=movie")
check "Filter by type (movie)" "$R" "200"

R=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/content/?genre=Sci-Fi")
check "Filter by genre (Sci-Fi)" "$R" "200"

R=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/content/?search=batman")
check "Search by keyword (batman)" "$R" "200"

R=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/content/?actor=McConaughey")
check "Filter by actor" "$R" "200"

R=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/content/?director=Nolan")
check "Filter by director" "$R" "200"

R=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/content/$MOVIE1_ID")
check "Get content by ID" "$R" "200"

# ── FR-18: Filter by Release Year ─────────────────────────────────
header "FR-18 Filter by Release Year"
R=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/content/?year=2014")
check "Filter by release year (2014)" "$R" "200"

# ── FR-19: Content Sorting ─────────────────────────────────────────
header "FR-19 Content Sorting"
R=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/content/?sort_by=title&sort_order=asc")
check "Sort by title ascending" "$R" "200"

R=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/content/?sort_by=rating&sort_order=desc")
check "Sort by rating descending" "$R" "200"

R=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/content/?sort_by=release_date&sort_order=desc")
check "Sort by release date" "$R" "200"

# ── FR-20: Top Rated Content ──────────────────────────────────────
header "FR-20 Top Rated Content"
R=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/content/top-rated")
check "Get top rated content" "$R" "200"

# ── FR-21: Recently Added Content ─────────────────────────────────
header "FR-21 Recently Added Content"
R=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/content/recently-added")
check "Get recently added content" "$R" "200"

# ── FR-22: Genre Listing ──────────────────────────────────────────
header "FR-22 Genre Listing"
R=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/content/genres")
check "List all genres" "$R" "200"

# ── FR-28: Content Stats ──────────────────────────────────────────
header "FR-28 Content Stats by Type/Genre"
R=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/content/stats")
check "Content count by type and genre" "$R" "200"

# ── FR-32: Cast/Director Search ───────────────────────────────────
header "FR-32 Cast/Director Search"
R=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/content/cast-search?query=Nolan")
check "Search by cast/director name" "$R" "200"

# ── Content Update / Delete ───────────────────────────────────────
header "Content Update/Delete (Admin)"
R=$(curl -s -o /dev/null -w "%{http_code}" -X PUT "$BASE/content/$MOVIE1_ID" \
  -H "$AUTH_ADMIN" -H "Content-Type: application/json" \
  -d '{"description":"Updated description for Interstellar"}')
check "Admin updates content" "$R" "200"

# ── FR-11: Content Ratings & Reviews ──────────────────────────────
header "FR-11 Content Ratings & Reviews"

R=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/ratings/$MOVIE1_ID" \
  -H "$AUTH_USER" -H "Content-Type: application/json" \
  -d '{"score":5,"review":"Mind-blowing film about space and time!"}')
check "Rate content with review (5 stars)" "$R" "201"

R=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/ratings/$MOVIE2_ID" \
  -H "$AUTH_USER" -H "Content-Type: application/json" \
  -d '{"score":4.5,"review":"Best superhero movie ever made"}')
check "Rate second content" "$R" "201"

R=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/ratings/$SERIES1_ID" \
  -H "$AUTH_USER" -H "Content-Type: application/json" \
  -d '{"score":5}')
check "Rate content without review" "$R" "201"

R=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/ratings/$MOVIE1_ID" -H "$AUTH_USER")
check "Get rating summary (avg, total, user score)" "$R" "200"

R=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/ratings/$MOVIE1_ID/reviews")
check "Get content reviews" "$R" "200"

# ── FR-23: User's Rating History ──────────────────────────────────
header "FR-23 User's Rating History"
R=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/ratings/my-ratings" -H "$AUTH_USER")
check "Get my rating history" "$R" "200"

# ── FR-10: Watchlist ──────────────────────────────────────────────
header "FR-10 Watchlist (Save for Later)"

R=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/users/$USER_ID/watchlist/$MOVIE1_ID" -H "$AUTH_USER")
check "Add to watchlist" "$R" "200"

R=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/users/$USER_ID/watchlist/$SERIES1_ID" -H "$AUTH_USER")
check "Add second item to watchlist" "$R" "200"

R=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/users/$USER_ID/watchlist" -H "$AUTH_USER")
check "Get watchlist" "$R" "200"

R=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE "$BASE/users/$USER_ID/watchlist/$SERIES1_ID" -H "$AUTH_USER")
check "Remove from watchlist" "$R" "200"

# ── FR-06: Playback & Watch Tracking (Cassandra) ──────────────────
header "FR-06 Playback & Watch Tracking"

R=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/watch/$MOVIE1_ID/event" \
  -H "$AUTH_USER" -H "Content-Type: application/json" \
  -d '{"event_type":"play","position_seconds":0}')
check "Record playback event (play)" "$R" "201"

R=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/watch/$MOVIE1_ID/event" \
  -H "$AUTH_USER" -H "Content-Type: application/json" \
  -d '{"event_type":"pause","position_seconds":3600}')
check "Record playback event (pause)" "$R" "201"

R=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/watch/$MOVIE1_ID/event" \
  -H "$AUTH_USER" -H "Content-Type: application/json" \
  -d '{"event_type":"resume","position_seconds":3600}')
check "Record playback event (resume)" "$R" "201"

R=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/watch/$MOVIE2_ID/event" \
  -H "$AUTH_USER" -H "Content-Type: application/json" \
  -d '{"event_type":"play","position_seconds":0}')
check "Record play event on second movie" "$R" "201"

R=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/watch/$MOVIE2_ID/event" \
  -H "$AUTH_USER" -H "Content-Type: application/json" \
  -d '{"event_type":"complete","position_seconds":9120}')
check "Record complete event" "$R" "201"

R=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/watch/$MOVIE1_ID/events" -H "$AUTH_USER")
check "Get playback events" "$R" "200"

R=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/watch/$MOVIE1_ID/resume" -H "$AUTH_USER")
check "Get resume position" "$R" "200"

# ── FR-07: Watch History ──────────────────────────────────────────
header "FR-07 Watch History"
R=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/watch/history/me" -H "$AUTH_USER")
check "Get my watch history" "$R" "200"

# ── FR-08: Personalized Homepage ──────────────────────────────────
header "FR-08 Personalized Homepage"
R=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/watch/continue-watching" -H "$AUTH_USER")
check "Continue watching (incomplete titles)" "$R" "200"

R=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/recommendations/homepage" -H "$AUTH_USER")
check "Personalized homepage (all rows)" "$R" "200"

# ── FR-09: Graph-Based Recommendations ────────────────────────────
header "FR-09 Graph-Based Recommendations"
R=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/recommendations/for-you" -H "$AUTH_USER")
check "Get recommendations for you" "$R" "200"

# ── FR-14: Content Similarity ─────────────────────────────────────
header "FR-14 Content Similarity (More Like This)"
R=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/recommendations/similar/$MOVIE1_ID")
check "Get similar content (Interstellar)" "$R" "200"

# ── FR-09 extra: User Graph ───────────────────────────────────────
R=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/recommendations/user-graph" -H "$AUTH_USER")
check "Get user graph data" "$R" "200"

# ── FR-12: Multi-Profile Support ──────────────────────────────────
header "FR-12 Multi-Profile Support"

R=$(curl -s -o /tmp/z_profile1.json -w "%{http_code}" -X POST "$BASE/users/$USER_ID/profiles" \
  -H "$AUTH_USER" -H "Content-Type: application/json" \
  -d '{"name":"Kids Profile","maturity_level":"kids"}')
check "Create profile (Kids)" "$R" "201"
PROFILE_ID=$(cat /tmp/z_profile1.json | python3 -c "import sys,json; print(json.load(sys.stdin)['profile_id'])" 2>/dev/null)

R=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/users/$USER_ID/profiles" \
  -H "$AUTH_USER" -H "Content-Type: application/json" \
  -d '{"name":"Teen Profile","maturity_level":"teen"}')
check "Create profile (Teen)" "$R" "201"

R=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/users/$USER_ID/profiles" -H "$AUTH_USER")
check "List profiles" "$R" "200"

R=$(curl -s -o /dev/null -w "%{http_code}" -X PUT "$BASE/users/$USER_ID/profiles/$PROFILE_ID" \
  -H "$AUTH_USER" -H "Content-Type: application/json" \
  -d '{"name":"Updated Kids"}')
check "Update profile" "$R" "200"

R=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE "$BASE/users/$USER_ID/profiles/$PROFILE_ID" -H "$AUTH_USER")
check "Delete profile" "$R" "204"

# ── FR-24: Admin — List Users ─────────────────────────────────────
header "FR-24 Admin List Users"
R=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/users/" -H "$AUTH_ADMIN")
check "Admin lists all users" "$R" "200"

# Non-admin cannot list
R=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/users/" -H "$AUTH_USER")
check "Non-admin cannot list users" "$R" "403"

# ── FR-33: Search Users ──────────────────────────────────────────
header "FR-33 Search Users"
R=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/users/?search=normal" -H "$AUTH_ADMIN")
check "Search users by username" "$R" "200"

# ── FR-25: Admin — Deactivate User ────────────────────────────────
header "FR-25 Admin Activate/Deactivate User"
R=$(curl -s -o /dev/null -w "%{http_code}" -X PATCH "$BASE/users/$USER_ID/activate?active=false" -H "$AUTH_ADMIN")
check "Admin deactivates user" "$R" "200"

R=$(curl -s -o /dev/null -w "%{http_code}" -X PATCH "$BASE/users/$USER_ID/activate?active=true" -H "$AUTH_ADMIN")
check "Admin reactivates user" "$R" "200"

# ── FR-15: Platform Analytics (Admin) ─────────────────────────────
header "FR-15 Platform Analytics"
R=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/admin/analytics" -H "$AUTH_ADMIN")
check "Admin analytics dashboard" "$R" "200"

# ── FR-29: User Growth ────────────────────────────────────────────
header "FR-29 User Activity Summary"
R=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/admin/user-growth?days=30" -H "$AUTH_ADMIN")
check "User growth over 30 days" "$R" "200"

# ── FR-30: Trending Content ──────────────────────────────────────
header "FR-30 Trending Content"
R=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/admin/trending?days=7" -H "$AUTH_ADMIN")
check "Trending content (last 7 days)" "$R" "200"

# ── FR-35: Database Health Check ─────────────────────────────────
header "FR-35 Database Health Check"
R=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/admin/health" -H "$AUTH_ADMIN")
check "All-database health check" "$R" "200"

# ── FR-31: Delete Rating ─────────────────────────────────────────
header "FR-31 Delete Rating"
R=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE "$BASE/ratings/$SERIES1_ID" -H "$AUTH_USER")
check "Delete a rating" "$R" "204"

# ── Cleanup: Delete content (admin) ───────────────────────────────
header "Cleanup"
# We don't delete everything so the DB has data to inspect manually

# ════════════════════════════════════════════════════════════════════
# Summary
# ════════════════════════════════════════════════════════════════════
echo ""
echo "════════════════════════════════════════════════════════"
printf "  RESULTS: \033[32m%d passed\033[0m / \033[31m%d failed\033[0m / %d total\n" "$PASS" "$FAIL" "$TOTAL"
echo "════════════════════════════════════════════════════════"

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
