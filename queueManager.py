import queue
from datetime import datetime
import time

class QueueItem:
    def __init__(self, track, user, user_id, **kwargs):
        self.track = track
        self.user = user
        self.user_id = user_id
        self.votes = kwargs.get('votes', [])
        self.queuedTimestamp = datetime.strptime(str(datetime.now()), "%Y-%m-%d %H:%M:%S.%f")

class QueueManager:
    def __init__(self):
        self.queue = []

    def put(self, item):
        self.queue.append(item)

    def get(self):
        if len(self.queue) < 1:
            return None
        return self.queue.pop(0)

    def front(self):
        return self.queue[0]

    def size(self):
        return len(self.queue)

    def empty(self):
        return not (len(self.queue))

    # Function to push element in last by
    # popping from front until size becomes 0
    def FrontToLast(self, qsize):
        # Base condition
        if qsize <= 0:
            return

        # pop front element and push
        # this last in a queue
        self.put(self.get())

        # Recursive call for pushing element
        self.FrontToLast(qsize - 1)

    # Function to push an element in the queue
    # while maintaining the sorted order
    def pushInQueue(self, temp, qsize):
        if not self.empty() or qsize != 0:
            diffTime = self.front().queuedTimestamp - temp.queuedTimestamp
            diffVotes = len(temp.votes) - len(self.front().votes)

        # Base condition
        if self.empty() or qsize == 0:
            self.put(temp)
            return

        # If current element has more votes than element at front
        if diffVotes > 0:

            # Call stack with front of queue
            self.put(temp)

            # Recursive call for inserting a front
            # element of the queue to the last
            self.FrontToLast(qsize)

        # If current has less votes than element at front
        elif diffVotes < 0:

            # Push front element into
            # last in a queue
            self.put(self.get())

            # Recursive call for inserting a front
            # element of the queue to the last
            self.pushInQueue(temp, qsize - 1)

        elif diffTime.seconds > 1*(10**-15) and diffTime.days >= 0:

            # Call stack with front of queue
            self.put(temp)

            # Recursive call for inserting a front
            # element of the queue to the last
            self.FrontToLast(qsize)

        else:

            # Push front element into
            # last in a queue
            self.put(self.get())

            # Recursive call for inserting a front
            # element of the queue to the last
            self.pushInQueue(temp, qsize - 1)

    # Function to sort the given
    # queue using recursion
    def sortQueue(self):
        # Return if queue is empty
        if self.empty():
            return

        # Get the front element which will
        # be stored in this variable
        # throughout the recursion stack
        temp = self.get()

        # Recursive call
        self.sortQueue()

        # Push the current element into the queue
        # according to the sorting order
        self.pushInQueue(temp, self.size())



