// frontend/src/components/FeedbackWidget.jsx
export default function FeedbackWidget({ messageId, conversationId }) {
  const [rating, setRating] = useState(0);
  const [feedback, setFeedback] = useState("");

  const submitFeedback = async () => {
    await api.post('/api/v1/feedback', {
      message_id: messageId,
      conversation_id: conversationId,
      relevance_score: rating,
      suggested_improvement: feedback
    });
    alert("Thank you! This helps improve search quality.");
  };

  return (
    <div className="feedback-widget">
      <p>Was this helpful?</p>
      <div className="stars">
        {[1, 2, 3, 4, 5].map(star => (
          <button 
            key={star} 
            onClick={() => setRating(star)}
            className={star <= rating ? "star-filled" : "star-empty"}
          >
            ⭐
          </button>
        ))}
      </div>
      <textarea 
        placeholder="Any suggestions to improve this answer?"
        value={feedback}
        onChange={(e) => setFeedback(e.target.value)}
      />
      <button onClick={submitFeedback}>Submit Feedback</button>
    </div>
  );
}