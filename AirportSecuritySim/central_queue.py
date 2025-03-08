import simpy
import random
import statistics


wait_times = []


class AirportSecurity:
    """
    a centralized system where all passengers queue for each stage:
    - boarding pass check
    - baggage screening
    - body screening
    each stage is modeled with a resource with a specified capacity.
    """
    def __init__(self, env, num_officers=4, num_baggage_screeners=4, num_body_screeners=4):
        self.env = env
        self.officer = simpy.Resource(env, capacity=num_officers)
        self.baggage_screener = simpy.Resource(env, capacity=num_baggage_screeners)
        self.body_screener = simpy.Resource(env, capacity=num_body_screeners)

    def check_boarding_pass(self, passenger):
        # Boarding pass check takes 20-40 seconds (0.3-0.7 minutes)
        yield self.env.timeout(random.uniform(0.3, 0.7))

    def scan_baggage(self, passenger):
        # Baggage screening takes 2-3 minutes
        yield self.env.timeout(random.uniform(2, 3))

    def scan_body(self, passenger):
        # Body screening takes 30-60 seconds (0.5-1 minute)
        yield self.env.timeout(random.uniform(0.5, 1))


def check_passenger(env, name, security, assigned_lane=None):
    arrival_time = env.now
    print(f"{name} arrives at time {env.now:.2f}")

    # stage 1: Boarding pass check (centralized queue)
    with security.officer.request() as req:
        yield req
        yield env.process(security.check_boarding_pass(name))

    # stage 2: Baggage screening (centralized queue)
    with security.baggage_screener.request() as req:
        yield req
        yield env.process(security.scan_baggage(name))

    # stage 3: Body screening (centralized queue)
    with security.body_screener.request() as req:
        yield req
        yield env.process(security.scan_body(name))

    total_time = env.now - arrival_time
    wait_times.append(total_time)
    print(f"{name} finishes at time {env.now:.2f} (Total time: {total_time:.2f} minutes)")


def get_mean_interarrival_time(current_time):
    """
    returns the mean interarrival time based on the current simulation time.
    - first 15 minutes: non-peak (1 minute on average)
    - 15 to 45 minutes: peak (0.5 minutes on average)
    - after 45 minutes: non-peak (1 minute on average)
    """
    if current_time < 10:
        return 1.0
    elif current_time < 50:
        return 0.5
    else:
        return 1.0


def passenger_arrivals(env, security):
    i = 0
    while True:
        # determine the mean interarrival time based on current time.
        mean_interarrival = get_mean_interarrival_time(env.now)
        # generate a new passenger after a interarrival time modeled after a Poisson distribution with a time-varying rate
        yield env.timeout(random.expovariate(1.0 / mean_interarrival))
        i += 1
        # kick off passenger's checking process
        env.process(check_passenger(env, f"Passenger {i}", security))


def run_airport(running_time, num_lanes):
    env = simpy.Environment()
    security = AirportSecurity(env, num_officers=2, num_baggage_screeners=6, num_body_screeners=2)

    # pre-populate the central queue with a few initial passengers (e.g. 2 passengers)
    initial_passengers = 2
    for j in range(initial_passengers):
        env.process(check_passenger(env, f"Initial Passenger {j + 1}", security))

    # average arrival rate of 2 passengers/min (decrease value to increase average)
    env.process(passenger_arrivals(env, security))
    env.run(until=running_time)


def calculate_wait_time():
    average_wait = statistics.mean(wait_times)
    minutes, frac_minutes = divmod(average_wait, 1)
    seconds = frac_minutes * 60
    return round(minutes), round(seconds)


def main():
    # run simulation for 60 minutes
    run_airport(60, 4)

    mins, secs = calculate_wait_time()
    print(
      f"\nThe average wait time is {mins} minutes and {secs} seconds.",
    )


if __name__ == "__main__":
    main()
