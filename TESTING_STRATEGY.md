# Comprehensive Testing Strategy for DM-Based Natural Language Task Creation

## 🎯 Testing Overview

This document outlines a comprehensive testing strategy for Bakushin's DM-based natural language task creation system, covering personality consistency, conversation flows, natural language parsing, and edge cases.

## 🧪 Testing Categories

### 1. Natural Language Parsing Tests

#### Basic Pattern Recognition

```python
# Test cases for frequency patterns
NL_PARSING_TEST_CASES = [
    # Daily patterns
    {
        'input': 'I want to work out daily',
        'expected': {
            'task_name': 'work out',
            'frequency_type': 'daily',
            'frequency_value': 1,
            'confidence': 0.9
        }
    },
    {
        'input': 'exercise every day at 7am',
        'expected': {
            'task_name': 'exercise',
            'frequency_type': 'daily',
            'time_preference': '7:00 AM',
            'confidence': 0.95
        }
    },

    # Weekly count patterns
    {
        'input': 'I want to work out 3 times a week',
        'expected': {
            'task_name': 'work out',
            'frequency_type': 'weekly_count',
            'frequency_value': 3,
            'confidence': 0.9
        }
    },
    {
        'input': 'go to gym twice per week',
        'expected': {
            'task_name': 'go to gym',
            'frequency_type': 'weekly_count',
            'frequency_value': 2,
            'confidence': 0.85
        }
    },

    # Specific days
    {
        'input': 'read every weekday morning',
        'expected': {
            'task_name': 'read',
            'frequency_type': 'specific_days',
            'frequency_value': ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'],
            'time_preference': 'morning',
            'confidence': 0.9
        }
    },
    {
        'input': 'meditate on weekends',
        'expected': {
            'task_name': 'meditate',
            'frequency_type': 'specific_days',
            'frequency_value': ['saturday', 'sunday'],
            'confidence': 0.85
        }
    },

    # Interval patterns
    {
        'input': 'run every other day',
        'expected': {
            'task_name': 'run',
            'frequency_type': 'interval',
            'frequency_value': 2,
            'confidence': 0.9
        }
    },
    {
        'input': 'yoga every two days',
        'expected': {
            'task_name': 'yoga',
            'frequency_type': 'interval',
            'frequency_value': 2,
            'confidence': 0.85
        }
    },

    # Time expressions
    {
        'input': 'workout in the morning',
        'expected': {
            'time_preference': 'morning',
            'parsed_time': '08:00'
        }
    },
    {
        'input': 'read before bed',
        'expected': {
            'time_preference': 'before bed',
            'parsed_time': '21:30'
        }
    },
    {
        'input': 'exercise at 6:30 AM',
        'expected': {
            'time_preference': '6:30 AM',
            'parsed_time': '06:30'
        }
    }
]
```

#### Edge Cases and Error Handling

```python
EDGE_CASE_TESTS = [
    # Ambiguous input
    {
        'input': 'I want to be healthy',
        'expected_behavior': 'ask_for_clarification',
        'confidence_threshold': 0.3
    },
    {
        'input': 'exercise',
        'expected_behavior': 'ask_for_frequency_and_time',
        'missing_info': ['frequency', 'time']
    },

    # Invalid frequencies
    {
        'input': 'work out 15 times a week',
        'expected_behavior': 'suggest_reasonable_alternative',
        'validation_error': 'frequency_too_high'
    },
    {
        'input': 'read 0 times per week',
        'expected_behavior': 'ask_for_clarification',
        'validation_error': 'invalid_frequency'
    },

    # Invalid times
    {
        'input': 'exercise at 25:00',
        'expected_behavior': 'ask_for_valid_time',
        'validation_error': 'invalid_time_format'
    },
    {
        'input': 'workout at midnight thirty',
        'expected_behavior': 'ask_for_clarification',
        'parsing_difficulty': 'complex_time_expression'
    },

    # Conflicting information
    {
        'input': 'daily workout 3 times a week',
        'expected_behavior': 'ask_for_clarification',
        'conflict_type': 'frequency_mismatch'
    }
]
```

### 2. Conversation Flow Tests

#### Onboarding Flow Tests

```python
ONBOARDING_FLOW_TESTS = [
    {
        'name': 'complete_onboarding_flow',
        'steps': [
            {
                'user_input': '/start',
                'expected_response_contains': ['yooo', 'whats ur name'],
                'conversation_state': 'name_collection'
            },
            {
                'user_input': 'John',
                'expected_response_contains': ['john', 'goals', '3 months'],
                'conversation_state': 'goal_setting'
            },
            {
                'user_input': 'I want to work out more',
                'expected_response_contains': ['fitness', 'specific', 'how many times'],
                'conversation_state': 'task_creation'
            },
            {
                'user_input': '3 times a week in the morning',
                'expected_response_contains': ['monday wednesday friday', '7am'],
                'conversation_state': 'time_collection'
            },
            {
                'user_input': '7am',
                'expected_response_contains': ['schedule', 'monday', 'wednesday', 'friday'],
                'conversation_state': 'confirmation'
            },
            {
                'user_input': 'yes',
                'expected_response_contains': ['LETS GOOOO', '$5/month', 'accountability'],
                'conversation_state': 'payment_prompt'
            }
        ]
    },

    {
        'name': 'name_rejection_flow',
        'steps': [
            {
                'user_input': '/start',
                'expected_response_contains': ['whats ur name']
            },
            {
                'user_input': 'x',
                'expected_response_contains': ['bruh', 'not a name'],
                'conversation_state': 'name_collection'  # Should stay in same state
            },
            {
                'user_input': 'Alex',
                'expected_response_contains': ['alex', 'goals'],
                'conversation_state': 'goal_setting'
            }
        ]
    }
]
```

#### Task Creation Flow Tests

```python
TASK_CREATION_FLOW_TESTS = [
    {
        'name': 'complete_task_creation',
        'initial_state': 'idle',
        'steps': [
            {
                'user_input': 'I want to read more',
                'expected_response_contains': ['intellectual', 'specific', 'how often'],
                'conversation_state': 'task_creation'
            },
            {
                'user_input': 'every day before bed',
                'expected_response_contains': ['9pm', '10pm', 'what time'],
                'conversation_state': 'time_collection'
            },
            {
                'user_input': '9:30 PM',
                'expected_response_contains': ['Daily Reading', '9:30 PM', 'sound good'],
                'conversation_state': 'confirmation'
            },
            {
                'user_input': 'yes',
                'expected_response_contains': ['created', 'remind you'],
                'conversation_state': 'idle'
            }
        ]
    },

    {
        'name': 'modification_during_creation',
        'steps': [
            {
                'user_input': 'workout 5 times a week',
                'expected_response_contains': ['5 times', 'what time']
            },
            {
                'user_input': 'actually make it 3 times',
                'expected_response_contains': ['3 times', 'monday wednesday friday'],
                'should_update_context': True
            }
        ]
    }
]
```

### 3. Personality Consistency Tests

#### Bakushin Voice Tests

```python
PERSONALITY_TESTS = [
    {
        'name': 'casual_tone_consistency',
        'test_scenarios': [
            {
                'context': 'greeting_new_user',
                'expected_elements': ['lowercase', 'slang', 'emoji_usage'],
                'forbidden_elements': ['formal_language', 'corporate_speak']
            },
            {
                'context': 'motivational_message',
                'expected_elements': ['lock in', 'lets gooo', 'built different'],
                'personality_traits': ['supportive', 'energetic']
            },
            {
                'context': 'calling_out_excuses',
                'expected_elements': ['bruh', 'cap', 'be fr'],
                'personality_traits': ['direct', 'sarcastic_but_supportive']
            }
        ]
    },

    {
        'name': 'horse_reference_integration',
        'test_scenarios': [
            {
                'context': 'motivational_message',
                'horse_reference_frequency': 0.15,  # 15% of messages
                'expected_horse_phrases': [
                    'gallop towards your goals',
                    'no horsing around',
                    'horsepower energy',
                    'straight from the horses mouth'
                ],
                'integration_quality': 'natural_not_forced'
            },
            {
                'context': 'streak_celebration',
                'possible_horse_references': [
                    'stallion energy',
                    'thoroughbred dedication',
                    'running at full gallop'
                ]
            }
        ]
    }
]
```

#### Response Appropriateness Tests

```python
RESPONSE_APPROPRIATENESS_TESTS = [
    {
        'name': 'context_awareness',
        'scenarios': [
            {
                'user_context': {'streak_count': 0, 'first_task': True},
                'expected_tone': 'encouraging_but_realistic',
                'avoid_tone': 'overly_enthusiastic'
            },
            {
                'user_context': {'streak_count': 10, 'consistent_user': True},
                'expected_tone': 'celebratory_and_motivational',
                'expected_elements': ['streak_acknowledgment', 'hype']
            },
            {
                'user_context': {'missed_days': 3, 'struggling': True},
                'expected_tone': 'supportive_reality_check',
                'expected_elements': ['understanding', 'gentle_push']
            }
        ]
    }
]
```

### 4. Integration Tests

#### End-to-End User Journey Tests

```python
E2E_TESTS = [
    {
        'name': 'complete_user_journey',
        'description': 'Full user journey from /start to first reminder',
        'steps': [
            'user_runs_start_command',
            'bot_initiates_dm_conversation',
            'user_provides_name_and_goals',
            'bot_parses_natural_language_goal',
            'bot_asks_clarifying_questions',
            'user_provides_missing_information',
            'bot_generates_task_schedule',
            'user_confirms_schedule',
            'bot_creates_tasks_in_database',
            'bot_prompts_for_payment',
            'scheduler_sends_first_reminder'
        ],
        'validation_points': [
            'conversation_state_transitions',
            'database_task_creation',
            'scheduler_integration',
            'personality_consistency'
        ]
    }
]
```

#### Error Recovery Tests

```python
ERROR_RECOVERY_TESTS = [
    {
        'name': 'ai_service_failure',
        'scenario': 'openai_api_unavailable',
        'expected_behavior': 'fallback_to_rule_based_parsing',
        'user_experience': 'graceful_degradation'
    },
    {
        'name': 'database_connection_failure',
        'scenario': 'database_temporarily_unavailable',
        'expected_behavior': 'inform_user_and_retry',
        'user_experience': 'transparent_error_handling'
    },
    {
        'name': 'dm_permissions_denied',
        'scenario': 'user_has_dms_disabled',
        'expected_behavior': 'inform_in_server_and_guide_to_enable',
        'fallback_option': 'server_based_interaction'
    }
]
```

## 🔧 Test Implementation Framework

### Unit Test Structure

```python
# tests/test_natural_language_parser.py
import pytest
from src.services.natural_language_parser import NaturalLanguageParser
from src.services.bakushin_personality import BakushinPersonality

class TestNaturalLanguageParser:

    @pytest.fixture
    def parser(self):
        return NaturalLanguageParser(mock_ai_handler)

    @pytest.mark.parametrize("input_text,expected", NL_PARSING_TEST_CASES)
    async def test_basic_pattern_recognition(self, parser, input_text, expected):
        result = await parser.parse_task_intent(input_text)

        assert result.task_name == expected['task_name']
        assert result.frequency_type == expected['frequency_type']
        assert result.confidence >= expected.get('confidence', 0.7)

    @pytest.mark.parametrize("input_text,expected_behavior", EDGE_CASE_TESTS)
    async def test_edge_cases(self, parser, input_text, expected_behavior):
        result = await parser.parse_task_intent(input_text)

        if expected_behavior == 'ask_for_clarification':
            assert result.confidence < 0.5
            assert len(result.missing_info) > 0
```

### Integration Test Structure

```python
# tests/test_conversation_flows.py
import pytest
from src.services.dm_conversation_manager import DMConversationManager

class TestConversationFlows:

    @pytest.fixture
    async def conversation_manager(self):
        return DMConversationManager(mock_bot, mock_db, mock_ai)

    @pytest.mark.asyncio
    async def test_complete_onboarding_flow(self, conversation_manager):
        user_id = 12345

        # Simulate complete onboarding conversation
        for step in ONBOARDING_FLOW_TESTS[0]['steps']:
            message = create_mock_message(user_id, step['user_input'])
            await conversation_manager.handle_dm_message(message)

            conversation = await conversation_manager.get_conversation(user_id)
            assert conversation.state.value == step['conversation_state']
```

### Personality Test Structure

```python
# tests/test_bakushin_personality.py
class TestBakushinPersonality:

    @pytest.fixture
    def personality(self):
        return BakushinPersonality()

    def test_horse_reference_frequency(self, personality):
        """Test that horse references appear at appropriate frequency"""
        responses = []
        for _ in range(100):
            response = personality.add_personality_to_reminder("workout", 5)
            responses.append(response)

        horse_references = sum(1 for r in responses if any(
            phrase in r.lower() for phrase in ['horse', 'gallop', 'stallion']
        ))

        # Should be around 15% (±5%)
        assert 10 <= horse_references <= 20

    def test_casual_tone_consistency(self, personality):
        """Test that responses maintain casual tone"""
        response = personality.generate_response(
            context={'name': 'John', 'goal_type': 'fitness'},
            tone=ConversationTone.GOAL_SETTING
        )

        # Check for casual elements
        assert any(word in response.lower() for word in ['yo', 'bruh', 'ngl', 'fr'])
        # Check against formal language
        assert not any(word in response for word in ['Please', 'Thank you', 'Sincerely'])
```

## 📊 Performance and Load Testing

### Response Time Tests

```python
PERFORMANCE_TESTS = [
    {
        'name': 'nl_parsing_response_time',
        'target': 'under_2_seconds',
        'test_cases': NL_PARSING_TEST_CASES,
        'concurrent_users': [1, 10, 50, 100]
    },
    {
        'name': 'conversation_state_management',
        'target': 'under_500ms',
        'operations': ['get_conversation', 'update_conversation', 'expire_conversation']
    }
]
```

### Memory Usage Tests

```python
MEMORY_TESTS = [
    {
        'name': 'conversation_state_memory_usage',
        'scenario': '1000_concurrent_conversations',
        'memory_limit': '100MB',
        'cleanup_verification': 'expired_conversations_removed'
    }
]
```

## 🎯 Success Criteria

### Functional Requirements

- ✅ Parse 90%+ of common natural language task requests correctly
- ✅ Maintain conversation context across multiple message exchanges
- ✅ Generate appropriate schedules for all supported frequency patterns
- ✅ Handle edge cases gracefully with helpful error messages
- ✅ Maintain Bakushin's personality consistently across all interactions

### Performance Requirements

- ✅ Natural language parsing: < 2 seconds response time
- ✅ Conversation state management: < 500ms operations
- ✅ Memory usage: < 100MB for 1000 concurrent conversations
- ✅ Horse reference frequency: 10-20% of motivational messages

### User Experience Requirements

- ✅ Conversation feels natural and engaging
- ✅ Error recovery is transparent and helpful
- ✅ Personality remains consistent but not repetitive
- ✅ Payment prompt feels natural, not pushy

This comprehensive testing strategy ensures that Bakushin's natural language task creation system works reliably while maintaining the engaging, casual personality that makes the bot unique.
